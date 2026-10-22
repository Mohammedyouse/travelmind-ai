import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
IMPORTER = BACKEND / "scripts" / "import_sqlite_to_postgres.py"


class TestSQLiteDataMigration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="travelmind-import-test-")
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)
        self.source = self.directory / "source.sqlite"
        self.target = self.directory / "target.sqlite"
        self._initialize_database(self.source)
        self._initialize_database(self.target)
        self._prepare_source()

    def _environment(self, target: Path) -> dict[str, str]:
        environment = os.environ.copy()
        environment["DATABASE_URL"] = f"sqlite:///{target.as_posix()}"
        return environment

    def _initialize_database(self, database: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND,
            env=self._environment(database),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_migration_preserves_cache_tables_created_before_revision(self):
        target = self.directory / "preexisting-cache.sqlite"
        environment = self._environment(target)
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "002_saas_features"],
            cwd=BACKEND,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(migration.returncode, 0, migration.stderr)

        connection = sqlite3.connect(target)
        try:
            connection.executescript(
                """
                CREATE TABLE cached_places (
                    id TEXT PRIMARY KEY, destination TEXT NOT NULL, name TEXT NOT NULL,
                    category TEXT NOT NULL, lat REAL, lon REAL, address TEXT, rating REAL,
                    price_level TEXT, admission_price TEXT, photo_url TEXT,
                    photo_attribution TEXT, description TEXT, website TEXT,
                    source TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE cached_accommodations (
                    id TEXT PRIMARY KEY, destination TEXT NOT NULL, name TEXT NOT NULL,
                    tier TEXT NOT NULL, stars INTEGER, rating REAL, price_per_night REAL,
                    currency TEXT NOT NULL DEFAULT 'USD', neighborhood TEXT, amenities TEXT DEFAULT '[]',
                    photo_url TEXT, booking_url TEXT,
                    pricing_type TEXT NOT NULL DEFAULT 'estimated_reference_rate',
                    source TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO cached_places (id, destination, name, category, source)
                VALUES ('existing-place', 'BBB', 'Existing place', 'sight', 'test');
                INSERT INTO cached_accommodations (id, destination, name, tier, source)
                VALUES ('existing-stay', 'BBB', 'Existing stay', 'budget', 'test');
                """
            )
            connection.commit()
        finally:
            connection.close()

        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(migration.returncode, 0, migration.stderr)

        connection = sqlite3.connect(target)
        try:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM cached_places").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM cached_accommodations").fetchone()[0],
                1,
            )
            accommodation_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(cached_accommodations)")
            }
            self.assertTrue({"price_usd", "price_inr"} <= accommodation_columns)
            self.assertEqual(
                connection.execute("SELECT version_num FROM alembic_version").fetchone()[0],
                "003_cached_travel_data",
            )
        finally:
            connection.close()

    def _prepare_source(self) -> None:
        connection = sqlite3.connect(self.source)
        try:
            connection.execute("DROP TABLE alembic_version")
            connection.execute("ALTER TABLE users DROP COLUMN is_active")
            connection.executemany(
                "INSERT INTO users (id, email, full_name, password_hash, role, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [("user-1", "user@example.test", "Test User", "test-hash", "traveler", "2026-01-01")],
            )
            connection.execute(
                "INSERT INTO trips (id, user_id, origin, destination, travelers, currency, status, "
                "preferences, plan_results, created_at) VALUES "
                "('trip-1', 'user-1', 'AAA', 'BBB', 1, 'USD', 'draft', '{}', '{}', '2026-01-02')"
            )
            connection.execute(
                "INSERT INTO itinerary_items (id, trip_id, day, title, cost, created_at) "
                "VALUES ('item-1', 'trip-1', 1, 'Test activity', 0, '2026-01-03')"
            )
            connection.execute(
                "INSERT INTO budget_snapshots (id, trip_id, currency, total, contingency) "
                "VALUES ('budget-1', 'trip-1', 'USD', 10, 1)"
            )
            connection.execute(
                "INSERT INTO conversations (id, trip_id, user_id, role, content, created_at) "
                "VALUES ('conversation-1', 'trip-1', 'user-1', 'user', 'Test conversation', '2026-01-04')"
            )
            connection.execute(
                "INSERT INTO preferences (id, user_id, key, value, created_at) "
                "VALUES ('preference-1', 'user-1', 'style', 'quiet', '2026-01-05')"
            )
            connection.execute(
                "INSERT INTO subscriptions (id, user_id, tier, status, cancel_at_period_end, created_at) "
                "VALUES ('subscription-1', 'user-1', 'free', 'active', 0, '2026-01-06')"
            )
            connection.execute(
                "INSERT INTO payments (id, user_id, trip_id, amount, created_at) "
                "VALUES ('payment-1', 'user-1', 'trip-1', 10, '2026-01-07')"
            )
            connection.execute(
                "INSERT INTO notifications (id, user_id, trip_id, type, title, message, created_at) "
                "VALUES ('notification-1', 'user-1', 'trip-1', 'system', 'Test', 'Test', '2026-01-08')"
            )
            connection.execute(
                "INSERT INTO provider_search_records (id, provider, query, status, created_at) "
                "VALUES ('search-1', 'test', 'query', 'ok', '2026-01-09')"
            )
            connection.execute(
                "INSERT INTO agent_execution_logs (id, trip_id, agent_name, status, created_at) "
                "VALUES ('log-1', 'trip-1', 'test-agent', 'ok', '2026-01-10')"
            )
            connection.execute(
                "INSERT INTO cached_places (id, destination, name, category, source) "
                "VALUES ('place-1', 'BBB', 'Test place', 'sight', 'test')"
            )
            connection.execute(
                "INSERT INTO cached_accommodations (id, destination, name, tier, source) "
                "VALUES ('stay-1', 'BBB', 'Test stay', 'budget', 'test')"
            )
            connection.commit()
        finally:
            connection.close()

    def _run_importer(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(IMPORTER), "--source", str(self.source), *arguments],
            cwd=BACKEND,
            env=self._environment(self.target),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_import_is_resumable_and_validates_all_tables(self):
        target = sqlite3.connect(self.target)
        try:
            target.execute(
                "INSERT INTO users (id, email, full_name, password_hash, is_active, role, created_at) "
                "VALUES ('user-1', 'user@example.test', 'Test User', 'test-hash', 1, "
                "'traveler', '2026-01-01')"
            )
            target.commit()
        finally:
            target.close()

        dry_run = self._run_importer("--allow-sqlite-target")
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertIn("users: source=1 already_matching=1 planned_insert=0", dry_run.stdout)
        self.assertIn("Dry run complete: no data was written.", dry_run.stdout)

        first = self._run_importer("--allow-sqlite-target", "--apply")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("Validation passed", first.stdout)

        second = self._run_importer("--allow-sqlite-target", "--apply")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("source=1 matched=1 target=1", second.stdout)

        validate = self._run_importer("--allow-sqlite-target", "--validate-only")
        self.assertEqual(validate.returncode, 0, validate.stderr)
        self.assertIn("active source users=1/1", validate.stdout)

        target = sqlite3.connect(self.target)
        try:
            self.assertEqual(target.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
            self.assertEqual(target.execute("SELECT is_active FROM users").fetchone()[0], 1)
            self.assertEqual(target.execute("SELECT COUNT(*) FROM trips").fetchone()[0], 1)
            self.assertEqual(target.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            target.close()

    def test_sqlite_target_is_rejected_without_explicit_test_only_flag(self):
        result = self._run_importer("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SQLite targets are disabled", result.stderr)

    def test_unique_key_conflict_is_preserved_and_stops_before_import(self):
        self._initialize_database(self.directory / "alternate-target.sqlite")
        self.target = self.directory / "alternate-target.sqlite"
        target = sqlite3.connect(self.target)
        try:
            target.execute(
                "INSERT INTO users (id, email, full_name, password_hash, is_active, role, created_at) "
                "VALUES ('other-user', 'user@example.test', 'Keep Existing', 'different-hash', 1, "
                "'traveler', '2026-01-01')"
            )
            target.commit()
        finally:
            target.close()

        result = self._run_importer("--allow-sqlite-target", "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflicting unique-key data", result.stderr)

        target = sqlite3.connect(self.target)
        try:
            self.assertEqual(target.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
            self.assertEqual(target.execute("SELECT COUNT(*) FROM trips").fetchone()[0], 0)
            self.assertEqual(
                target.execute("SELECT full_name FROM users").fetchone()[0],
                "Keep Existing",
            )
        finally:
            target.close()

    def test_conflicting_existing_rows_are_not_overwritten_or_partially_imported(self):
        target = sqlite3.connect(self.target)
        try:
            target.execute(
                "INSERT INTO users (id, email, full_name, password_hash, is_active, role, created_at) "
                "VALUES ('user-1', 'user@example.test', 'Keep Existing', 'different-hash', 1, "
                "'traveler', '2026-01-01')"
            )
            target.commit()
        finally:
            target.close()

        result = self._run_importer("--allow-sqlite-target", "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflicting primary-key data", result.stderr)

        target = sqlite3.connect(self.target)
        try:
            self.assertEqual(target.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
            self.assertEqual(target.execute("SELECT COUNT(*) FROM trips").fetchone()[0], 0)
            self.assertEqual(
                target.execute("SELECT full_name FROM users").fetchone()[0],
                "Keep Existing",
            )
        finally:
            target.close()

    def test_backup_verification_checks_all_rows_without_target_database(self):
        backup = self.directory / "backup.sqlite"
        source_connection = sqlite3.connect(self.source)
        backup_connection = sqlite3.connect(backup)
        try:
            source_connection.backup(backup_connection)
        finally:
            backup_connection.close()
            source_connection.close()

        result = subprocess.run(
            [
                sys.executable,
                str(IMPORTER),
                "--source",
                str(self.source),
                "--verify-backup",
                str(backup),
            ],
            cwd=BACKEND,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("schema and all rows match", result.stdout)


if __name__ == "__main__":
    unittest.main()
