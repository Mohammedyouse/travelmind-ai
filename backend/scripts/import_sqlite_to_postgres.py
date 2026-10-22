"""Safely import the backend SQLite dataset into a migrated PostgreSQL database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator, Sequence

from sqlalchemy import MetaData, Table, and_, create_engine, func, inspect, select
from sqlalchemy.engine import Connection, Engine, URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool


MIGRATION_HEAD = "003_cached_travel_data"
TABLE_ORDER = (
    "users",
    "trips",
    "itinerary_items",
    "budget_snapshots",
    "conversations",
    "preferences",
    "subscriptions",
    "payments",
    "notifications",
    "provider_search_records",
    "agent_execution_logs",
    "cached_places",
    "cached_accommodations",
)
TABLES = frozenset(TABLE_ORDER)
BOOLEAN_COLUMNS = {
    ("users", "is_active"),
    ("subscriptions", "cancel_at_period_end"),
}
OWNERSHIP_RELATIONSHIPS = (
    (
        "conversations",
        "conversations.trip_id",
        "conversations.user_id",
        "trips",
        "trips.id",
        "trips.user_id",
    ),
    (
        "payments",
        "payments.trip_id",
        "payments.user_id",
        "trips",
        "trips.id",
        "trips.user_id",
    ),
    (
        "notifications",
        "notifications.trip_id",
        "notifications.user_id",
        "trips",
        "trips.id",
        "trips.user_id",
    ),
)
BATCH_SIZE = 500


class ImportErrorSafe(RuntimeError):
    """An actionable migration error that contains no row data or credentials."""


def _quote_sqlite_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _read_only_sqlite(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ImportErrorSafe(f"SQLite file does not exist: {path}")
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("BEGIN")
    return connection


def _sqlite_table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _sqlite_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    table = _quote_sqlite_identifier(table_name)
    return [row["name"] for row in connection.execute(f"PRAGMA table_info({table})")]


def _sqlite_rows(connection: sqlite3.Connection, table_name: str) -> Iterator[list[sqlite3.Row]]:
    cursor = connection.execute(f"SELECT * FROM {_quote_sqlite_identifier(table_name)}")
    while rows := cursor.fetchmany(BATCH_SIZE):
        yield rows


def _mapped_row(table_name: str, columns: Sequence[str], row: Sequence[Any]) -> dict[str, Any]:
    values = dict(zip(columns, row))
    if table_name == "users" and "is_active" not in values:
        values["is_active"] = True
    for column in columns:
        if (table_name, column) in BOOLEAN_COLUMNS and values[column] is not None:
            if values[column] not in (0, 1, False, True):
                raise ImportErrorSafe(f"Unexpected boolean value in {table_name}.{column}")
            values[column] = bool(values[column])
    return values


def _check_sqlite_foreign_keys(connection: sqlite3.Connection) -> int:
    failures = 0
    for table_name in TABLE_ORDER:
        groups: dict[int, list[sqlite3.Row]] = defaultdict(list)
        for row in connection.execute(
            f"PRAGMA foreign_key_list({_quote_sqlite_identifier(table_name)})"
        ):
            groups[row["id"]].append(row)
        child = _quote_sqlite_identifier(table_name)
        for rows in groups.values():
            rows.sort(key=lambda row: row["seq"])
            parent = _quote_sqlite_identifier(rows[0]["table"])
            join_conditions = " AND ".join(
                f"parent.{_quote_sqlite_identifier(row['to'])} = "
                f"child.{_quote_sqlite_identifier(row['from'])}"
                for row in rows
            )
            non_null_conditions = " AND ".join(
                f"child.{_quote_sqlite_identifier(row['from'])} IS NOT NULL"
                for row in rows
            )
            query = (
                f"SELECT COUNT(*) FROM {child} AS child "
                f"WHERE {non_null_conditions} AND NOT EXISTS "
                f"(SELECT 1 FROM {parent} AS parent WHERE {join_conditions})"
            )
            failures += int(connection.execute(query).fetchone()[0])
    return failures


def _check_ownership_relationships(connection: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table, trip_ref, owner_ref, _, trip_id_ref, trip_owner_ref in OWNERSHIP_RELATIONSHIPS:
        table_name, trip_column = trip_ref.split(".", 1)
        _, owner_column = owner_ref.split(".", 1)
        _, trip_id_column = trip_id_ref.split(".", 1)
        _, trip_owner_column = trip_owner_ref.split(".", 1)
        query = (
            f"SELECT COUNT(*) FROM {_quote_sqlite_identifier(table_name)} AS child "
            f"JOIN trips AS parent ON parent.{_quote_sqlite_identifier(trip_id_column)} = "
            f"child.{_quote_sqlite_identifier(trip_column)} "
            f"WHERE child.{_quote_sqlite_identifier(trip_column)} IS NOT NULL "
            f"AND child.{_quote_sqlite_identifier(owner_column)} <> "
            f"parent.{_quote_sqlite_identifier(trip_owner_column)}"
        )
        counts[table] = int(connection.execute(query).fetchone()[0])
    return counts


def _validate_source(connection: sqlite3.Connection) -> tuple[dict[str, int], dict[str, list[str]]]:
    table_names = _sqlite_table_names(connection)
    missing = TABLES - table_names
    unexpected = table_names - TABLES
    if missing:
        raise ImportErrorSafe(f"Source is missing required tables: {', '.join(sorted(missing))}")
    if unexpected:
        raise ImportErrorSafe(
            "Source contains unrecognized tables; refusing to omit them: "
            + ", ".join(sorted(unexpected))
        )

    integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    if integrity != ["ok"]:
        raise ImportErrorSafe("Source SQLite integrity_check failed")
    fk_errors = _check_sqlite_foreign_keys(connection)
    if fk_errors:
        raise ImportErrorSafe(f"Source contains {fk_errors} foreign-key violations")

    ownership_errors = _check_ownership_relationships(connection)
    if any(ownership_errors.values()):
        raise ImportErrorSafe("Source contains trip/user ownership mismatches")
    duplicate_emails = int(
        connection.execute(
            "SELECT COUNT(*) FROM ("
            "SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1"
            ")"
        ).fetchone()[0]
    )
    if duplicate_emails:
        raise ImportErrorSafe("Source contains duplicate user email keys")

    source_columns = {table: _sqlite_columns(connection, table) for table in TABLE_ORDER}

    counts = {
        table: int(
            connection.execute(
                f"SELECT COUNT(*) FROM {_quote_sqlite_identifier(table)}"
            ).fetchone()[0]
        )
        for table in TABLE_ORDER
    }
    return counts, source_columns


def _normalise_target_url(raw_url: str, allow_sqlite_target: bool) -> URL:
    try:
        url = make_url(raw_url)
    except (TypeError, ValueError) as error:
        raise ImportErrorSafe("The target database URL is invalid") from error

    if url.drivername in {"postgres", "postgresql"} or url.drivername.startswith("postgresql+"):
        url = url.set(drivername="postgresql+psycopg")
        query = dict(url.query)
        query.setdefault("sslmode", "require")
        url = url.set(query=query)
        return url
    if url.drivername.startswith("sqlite") and allow_sqlite_target:
        return url
    if url.drivername.startswith("sqlite"):
        raise ImportErrorSafe(
            "SQLite targets are disabled; pass --allow-sqlite-target only for disposable local tests"
        )
    raise ImportErrorSafe("Target must be PostgreSQL (SQLite is allowed only for local tests)")


def _create_target_engine(url: URL) -> Engine:
    if url.drivername.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )


def _check_target_schema(
    connection: Connection,
    target_tables: dict[str, Table],
    source_columns: dict[str, list[str]],
) -> None:
    inspector = inspect(connection)
    available = set(inspector.get_table_names())
    missing = TABLES - available
    if missing:
        raise ImportErrorSafe(
            "Target schema is incomplete; run the approved Alembic migration first. Missing: "
            + ", ".join(sorted(missing))
        )
    if "alembic_version" not in available:
        raise ImportErrorSafe("Target has no alembic_version table; migrate it before importing")

    version_table = Table("alembic_version", MetaData(), autoload_with=connection)
    versions = list(connection.execute(select(version_table.c.version_num)).scalars())
    if versions != [MIGRATION_HEAD]:
        raise ImportErrorSafe(
            f"Target migration revision must be exactly {MIGRATION_HEAD}; no schema changes were made"
        )

    for table_name in TABLE_ORDER:
        target_columns = set(target_tables[table_name].c.keys())
        source_column_set = set(source_columns[table_name])
        missing_target_columns = source_column_set - target_columns
        missing_source_columns = target_columns - source_column_set
        if table_name == "users":
            missing_source_columns.discard("is_active")
        if missing_target_columns:
            raise ImportErrorSafe(
                f"Source table {table_name} has columns not represented by the target: "
                + ", ".join(sorted(missing_target_columns))
            )
        if missing_source_columns:
            raise ImportErrorSafe(
                f"Source table {table_name} is missing required columns: "
                + ", ".join(sorted(missing_source_columns))
            )


def _reflected_tables(connection: Connection) -> dict[str, Table]:
    metadata = MetaData()
    return {
        name: Table(name, metadata, autoload_with=connection)
        for name in TABLE_ORDER
    }


def _target_unique_columns(connection: Connection, table_name: str) -> list[str]:
    inspector = inspect(connection)
    candidates: set[tuple[str, ...]] = set()
    for constraint in inspector.get_unique_constraints(table_name):
        columns = tuple(constraint.get("column_names") or ())
        if columns and columns != ("id",):
            candidates.add(columns)
    for index in inspector.get_indexes(table_name):
        columns = tuple(index.get("column_names") or ())
        if index.get("unique") and columns and columns != ("id",):
            candidates.add(columns)
    if any(len(columns) != 1 for columns in candidates):
        raise ImportErrorSafe(
            f"Unsupported composite unique key on target table {table_name}; refusing import"
        )
    return sorted({columns[0] for columns in candidates})


def _target_row_map(connection: Connection, table: Table, ids: Sequence[Any]) -> dict[Any, dict[str, Any]]:
    if not ids:
        return {}
    rows = connection.execute(select(table).where(table.c.id.in_(ids))).mappings()
    return {row["id"]: dict(row) for row in rows}


def _values_match(table_name: str, expected: dict[str, Any], existing: dict[str, Any]) -> bool:
    for column, value in expected.items():
        actual = existing.get(column)
        if (table_name, column) in BOOLEAN_COLUMNS:
            actual = None if actual is None else bool(actual)
            value = None if value is None else bool(value)
        if actual != value:
            return False
    return True


def _preflight_table(
    connection: Connection,
    target: Table,
    source: sqlite3.Connection,
    source_columns: list[str],
) -> tuple[int, int]:
    total = 0
    already_present = 0
    unique_columns = _target_unique_columns(connection, target.name)
    for rows in _sqlite_rows(source, target.name):
        mapped_rows = [_mapped_row(target.name, source_columns, tuple(row)) for row in rows]
        ids = [row["id"] for row in mapped_rows]
        existing_by_id = _target_row_map(connection, target, ids)
        for row in mapped_rows:
            existing = existing_by_id.get(row["id"])
            if existing is None:
                continue
            if not _values_match(target.name, row, existing):
                raise ImportErrorSafe(
                    f"Conflicting primary-key data found in target table {target.name}; "
                    "existing data was not overwritten"
                )
            already_present += 1

        for unique_column in unique_columns:
            values_to_ids = {
                row[unique_column]: row["id"]
                for row in mapped_rows
                if row.get(unique_column) is not None
            }
            if not values_to_ids:
                continue
            matching = connection.execute(
                select(target.c.id, target.c[unique_column]).where(
                    target.c[unique_column].in_(list(values_to_ids))
                )
            )
            for existing_id, existing_value in matching:
                source_id = values_to_ids[existing_value]
                if existing_id != source_id:
                    raise ImportErrorSafe(
                        f"Conflicting unique-key data found in target table {target.name}; "
                        "existing data was not overwritten"
                    )
        total += len(mapped_rows)
    return total, already_present


def _insert_rows(connection: Connection, target: Table, values: list[dict[str, Any]]) -> None:
    if not values:
        return
    dialect = connection.dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise ImportErrorSafe("Unsupported target database dialect")
    connection.execute(insert(target).on_conflict_do_nothing(), values)


def _insert_table(
    engine: Engine,
    target: Table,
    source: sqlite3.Connection,
    source_columns: list[str],
    expected_count: int,
) -> None:
    with engine.begin() as connection:
        inserted_source_count = 0
        for rows in _sqlite_rows(source, target.name):
            mapped_rows = [_mapped_row(target.name, source_columns, tuple(row)) for row in rows]
            _insert_rows(connection, target, mapped_rows)
            inserted_source_count += len(mapped_rows)
        if inserted_source_count != expected_count:
            raise ImportErrorSafe(f"Source table {target.name} changed during import; table rolled back")
        matched, missing = _verify_table_rows(connection, target, source, source_columns)
        if matched != expected_count or missing:
            raise ImportErrorSafe(
                f"Imported rows did not match source table {target.name}; table rolled back"
            )


def _verify_table_rows(
    connection: Connection,
    target: Table,
    source: sqlite3.Connection,
    source_columns: list[str],
) -> tuple[int, int]:
    matched = 0
    missing = 0
    for rows in _sqlite_rows(source, target.name):
        mapped_rows = [_mapped_row(target.name, source_columns, tuple(row)) for row in rows]
        existing_by_id = _target_row_map(
            connection, target, [row["id"] for row in mapped_rows]
        )
        for expected in mapped_rows:
            actual = existing_by_id.get(expected["id"])
            if actual is None:
                missing += 1
            elif not _values_match(target.name, expected, actual):
                raise ImportErrorSafe(
                    f"Target data differs from source in table {target.name}; "
                    "existing data was not overwritten"
                )
            else:
                matched += 1
    return matched, missing


def _target_foreign_key_errors(connection: Connection) -> int:
    inspector = inspect(connection)
    errors = 0
    for table_name in TABLE_ORDER:
        child = Table(table_name, MetaData(), autoload_with=connection)
        for foreign_key in inspector.get_foreign_keys(table_name):
            parent_name = foreign_key.get("referred_table")
            child_columns = foreign_key.get("constrained_columns") or []
            parent_columns = foreign_key.get("referred_columns") or []
            if not parent_name or not child_columns or len(child_columns) != len(parent_columns):
                raise ImportErrorSafe(f"Invalid foreign-key definition on target table {table_name}")
            parent = Table(parent_name, MetaData(), autoload_with=connection)
            join_clause = and_(
                *(
                    child.c[child_column] == parent.c[parent_column]
                    for child_column, parent_column in zip(child_columns, parent_columns)
                )
            )
            non_null = and_(*(child.c[column].is_not(None) for column in child_columns))
            missing_parent = parent.c[parent_columns[0]].is_(None)
            query = (
                select(func.count())
                .select_from(child.outerjoin(parent, join_clause))
                .where(non_null, missing_parent)
            )
            errors += int(connection.execute(query).scalar_one())
    return errors


def _target_ownership_errors(connection: Connection) -> dict[str, int]:
    errors: dict[str, int] = {}
    for table_name, trip_ref, owner_ref, _, trip_id_ref, trip_owner_ref in OWNERSHIP_RELATIONSHIPS:
        child = Table(table_name, MetaData(), autoload_with=connection)
        trips = Table("trips", MetaData(), autoload_with=connection)
        _, trip_column = trip_ref.split(".", 1)
        _, owner_column = owner_ref.split(".", 1)
        _, trip_id_column = trip_id_ref.split(".", 1)
        _, trip_owner_column = trip_owner_ref.split(".", 1)
        query = (
            select(func.count())
            .select_from(child.join(trips, child.c[trip_column] == trips.c[trip_id_column]))
            .where(child.c[trip_column].is_not(None), child.c[owner_column] != trips.c[trip_owner_column])
        )
        errors[table_name] = int(connection.execute(query).scalar_one())
    return errors


def _print_validation(
    connection: Connection,
    target_tables: dict[str, Table],
    source: sqlite3.Connection,
    source_counts: dict[str, int],
    source_columns: dict[str, list[str]],
) -> None:
    problems: list[str] = []
    for table_name in TABLE_ORDER:
        table = target_tables[table_name]
        matched, missing = _verify_table_rows(
            connection, table, source, source_columns[table_name]
        )
        target_count = int(
            connection.execute(select(func.count()).select_from(table)).scalar_one()
        )
        if missing or matched != source_counts[table_name]:
            problems.append(table_name)
        print(
            f"{table_name}: source={source_counts[table_name]} "
            f"matched={matched} target={target_count} "
            f"additional_target_rows={target_count - matched}"
        )

    fk_errors = _target_foreign_key_errors(connection)
    ownership_errors = _target_ownership_errors(connection)
    inactive_source_users = 0
    users = target_tables["users"]
    for rows in _sqlite_rows(source, "users"):
        user_ids = [row["id"] for row in rows]
        inactive_source_users += int(
            connection.execute(
                select(func.count())
                .select_from(users)
                .where(users.c.id.in_(user_ids), users.c.is_active.is_(False))
            ).scalar_one()
        )
    if fk_errors:
        problems.append(f"{fk_errors} target foreign-key violations")
    if any(ownership_errors.values()):
        problems.append("target trip/user ownership mismatches")
    if inactive_source_users:
        problems.append("source users were not mapped to is_active=true")
    if problems:
        raise ImportErrorSafe("Validation failed: " + "; ".join(problems))
    print(
        f"Validation passed: source rows matched; target foreign-key violations={fk_errors}; "
        f"ownership mismatches={sum(ownership_errors.values())}; "
        f"active source users={source_counts['users'] - inactive_source_users}/{source_counts['users']}"
    )


def _row_digest(connection: sqlite3.Connection, table_name: str) -> tuple[int, str]:
    quoted = _quote_sqlite_identifier(table_name)
    primary_key_columns = [
        row["name"]
        for row in sorted(
            (
                row
                for row in connection.execute(f"PRAGMA table_info({quoted})")
                if row["pk"]
            ),
            key=lambda row: row["pk"],
        )
    ]
    order_by = ", ".join(_quote_sqlite_identifier(name) for name in primary_key_columns) or "rowid"
    cursor = connection.execute(f"SELECT * FROM {quoted} ORDER BY {order_by}")
    digest = hashlib.sha256()
    count = 0
    while rows := cursor.fetchmany(BATCH_SIZE):
        for row in rows:
            serializable = [
                {"bytes": value.hex()} if isinstance(value, bytes) else value
                for value in row
            ]
            digest.update(
                json.dumps(
                    serializable, ensure_ascii=False, separators=(",", ":"), sort_keys=True
                ).encode("utf-8")
            )
            digest.update(b"\n")
            count += 1
    return count, digest.hexdigest()


def _verify_backup(source_path: Path, backup_path: Path) -> int:
    source = _read_only_sqlite(source_path)
    backup = _read_only_sqlite(backup_path)
    try:
        source_schema = source.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE type IN ('table', 'index', 'trigger', 'view') ORDER BY type, name"
        ).fetchall()
        backup_schema = backup.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE type IN ('table', 'index', 'trigger', 'view') ORDER BY type, name"
        ).fetchall()
        if [tuple(row) for row in source_schema] != [tuple(row) for row in backup_schema]:
            raise ImportErrorSafe("Backup schema differs from the selected source")
        tables = _sqlite_table_names(source)
        if tables != _sqlite_table_names(backup):
            raise ImportErrorSafe("Backup table set differs from the selected source")
        verified_tables = 0
        for table_name in sorted(tables):
            if _row_digest(source, table_name) != _row_digest(backup, table_name):
                raise ImportErrorSafe(f"Backup rows differ in table {table_name}")
            verified_tables += 1
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ImportErrorSafe("Source SQLite integrity_check failed")
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ImportErrorSafe("Backup SQLite integrity_check failed")
        source_fk_errors = _check_sqlite_foreign_keys(source)
        backup_fk_errors = _check_sqlite_foreign_keys(backup)
        if source_fk_errors or backup_fk_errors:
            raise ImportErrorSafe("Source or backup contains foreign-key violations")
        print(
            f"Backup verified: schema and all rows match across {verified_tables} tables; "
            "integrity_check=ok; foreign-key violations=0"
        )
        return 0
    finally:
        source.close()
        backup.close()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Idempotently import a SQLite snapshot into an Alembic-migrated PostgreSQL database."
    )
    parser.add_argument("--source", required=True, type=Path, help="SQLite source snapshot")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="write missing rows; default is read-only preflight")
    mode.add_argument("--validate-only", action="store_true", help="verify an already-imported dataset")
    mode.add_argument("--verify-backup", type=Path, help="compare the source database with a SQLite backup")
    parser.add_argument(
        "--database-url-env",
        default="DATABASE_URL",
        help="environment variable holding the target URL (default: DATABASE_URL)",
    )
    parser.add_argument(
        "--allow-sqlite-target",
        action="store_true",
        help="allow only a disposable local SQLite target for tests; never use for production",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    source_path = args.source.resolve()

    if args.verify_backup is not None:
        return _verify_backup(source_path, args.verify_backup.resolve())

    raw_url = os.environ.get(args.database_url_env)
    if not raw_url:
        raise ImportErrorSafe(
            f"Target URL is missing from environment variable {args.database_url_env}"
        )
    target_url = _normalise_target_url(raw_url, args.allow_sqlite_target)
    if target_url.drivername.startswith("sqlite"):
        if not target_url.database or target_url.database == ":memory:":
            raise ImportErrorSafe("Disposable SQLite test target must be an existing file")
        target_path = Path(target_url.database).resolve()
        if target_path == source_path:
            raise ImportErrorSafe("Source and target must be different files")
        if not target_path.is_file():
            raise ImportErrorSafe(
                "Disposable SQLite test target must already exist; refusing to create a file"
            )

    source = _read_only_sqlite(source_path)
    engine = _create_target_engine(target_url)
    try:
        source_counts, source_columns = _validate_source(source)
        with engine.connect() as connection:
            target_tables = _reflected_tables(connection)
            _check_target_schema(connection, target_tables, source_columns)

            plans: dict[str, tuple[int, int]] = {}
            for table_name in TABLE_ORDER:
                plans[table_name] = _preflight_table(
                    connection,
                    target_tables[table_name],
                    source,
                    source_columns[table_name],
                )

        if args.validate_only:
            if any(count != matching for count, matching in plans.values()):
                missing = sum(count - matching for count, matching in plans.values())
                raise ImportErrorSafe(
                    f"Validation-only found {missing} source rows not yet present; no data was written"
                )
            with engine.connect() as connection:
                _print_validation(
                    connection, target_tables, source, source_counts, source_columns
                )
            return 0

        if not args.apply:
            for table_name in TABLE_ORDER:
                count, matching = plans[table_name]
                print(
                    f"{table_name}: source={count} already_matching={matching} "
                    f"planned_insert={count - matching}"
                )
            print("Dry run complete: no data was written.")
            return 0

        for table_name in TABLE_ORDER:
            count, matching = plans[table_name]
            if count == matching:
                continue
            _insert_table(
                engine,
                target_tables[table_name],
                source,
                source_columns[table_name],
                count,
            )
            print(f"{table_name}: table transaction committed; source rows={count}")

        with engine.connect() as connection:
            _print_validation(connection, target_tables, source, source_counts, source_columns)
        return 0
    finally:
        source.close()
        engine.dispose()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ImportErrorSafe as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    except SQLAlchemyError as error:
        print(
            f"ERROR: database operation failed ({type(error).__name__}); "
            "connection details and row values were suppressed",
            file=sys.stderr,
        )
        raise SystemExit(1)
