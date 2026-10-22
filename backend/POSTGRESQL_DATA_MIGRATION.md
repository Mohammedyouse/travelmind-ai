# PostgreSQL data migration

This procedure imports the backend dataset from `backend/travelmind.db` into an
already-migrated PostgreSQL database. The root-level `travelmind.db` is a
separate dataset and is not part of this procedure.

The importer never creates tables. It requires Alembic revision
`003_cached_travel_data`, including `cached_places` and
`cached_accommodations`. Its default mode is a read-only preflight. Use
`--apply` only after reviewing the preflight and receiving approval to write
data.

## Safety properties

- The SQLite source is opened read-only.
- All 13 application tables are required. Unknown or missing source tables,
  invalid foreign keys, and trip/user ownership mismatches stop the import.
- Users are inserted before trips and dependent rows. The remaining order
  follows foreign-key dependencies; both cache tables are included.
- A missing source `users.is_active` column is mapped to `true`. Existing
  values are retained if that column is present.
- Existing target rows are never updated or deleted. Identical primary-key
  rows are skipped. A different row with the same primary or unique key stops
  the run; the current table transaction rolls back.
- Each table is committed in its own transaction. A stopped run can be
  repeated: matching rows are skipped and remaining rows are inserted.
- Validation compares each source row by primary key and value, reports source
  and target row counts, checks target foreign keys, and verifies that source
  users are active and trip-linked conversations, payments, and notifications
  belong to the trip owner.
- Database URLs are read from the `DATABASE_URL` environment variable and are
  never printed. For PostgreSQL, the importer uses `psycopg` and defaults to
  `sslmode=require` if no SSL mode is present.
- `--allow-sqlite-target` exists only for disposable local tests. Never pass it
  for a production import.

## Backups currently verified

At the time this procedure was prepared, both local databases were backed up
outside the repository using SQLite's online backup API:

- Primary backend source:
  `C:\Users\USER\travelmind-ai-backups\backend-travelmind-20261023-023451.sqlite`
- Separate root database:
  `C:\Users\USER\travelmind-ai-backups\root-travelmind-20261023-023451.sqlite`

Both backups had matching schemas and row-content hashes, passed
`PRAGMA integrity_check`, and had zero foreign-key violations. The root backup
must remain separate. Create and verify a fresh backend backup immediately
before cutover if the source database has changed since these snapshots.

## Execution after explicit approval

Run from `backend` in PowerShell. Ensure the `DATABASE_URL` environment
variable is supplied from an approved local secret manager or other secure
environment mechanism. Do not put the URL in a command argument, source file,
or chat. Stop application writes for the cutover window.

```powershell
Set-Location 'C:\Users\USER\OneDrive\Desktop\n8n\travelmind-ai\backend'
$python = 'C:\Users\USER\OneDrive\Desktop\n8n\.venv\Scripts\python.exe'
$original = 'C:\Users\USER\OneDrive\Desktop\n8n\travelmind-ai\backend\travelmind.db'
$backupDir = 'C:\Users\USER\travelmind-ai-backups'
$source = Join-Path $backupDir ("backend-travelmind-{0}.sqlite" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

if (-not $env:DATABASE_URL) { throw 'Set DATABASE_URL through the approved secure environment mechanism first.' }
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
if (Test-Path -LiteralPath $source) { throw 'Refusing to overwrite an existing backup.' }

# Create a consistent snapshot using SQLite's online backup API.
$env:SOURCE_SQLITE = $original
$env:BACKUP_SQLITE = $source
@'
import os
import sqlite3
from pathlib import Path

source = sqlite3.connect(Path(os.environ["SOURCE_SQLITE"]).resolve().as_uri() + "?mode=ro", uri=True)
backup = sqlite3.connect(os.environ["BACKUP_SQLITE"])
try:
    source.backup(backup)
    backup.commit()
finally:
    backup.close()
    source.close()
'@ | & $python -
if ($LASTEXITCODE -ne 0) { throw 'SQLite backup creation failed.' }

# Re-check the backup before connecting to PostgreSQL.
& $python .\scripts\import_sqlite_to_postgres.py --source $original --verify-backup $source
if ($LASTEXITCODE -ne 0) { throw 'SQLite backup verification failed.' }

# This applies schema DDL to the selected Neon database; run only after approval.
& $python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Alembic upgrade failed.' }
& $python -m alembic current
if ($LASTEXITCODE -ne 0) { throw 'Could not verify the Alembic revision.' }

# Read-only target preflight: review every table's planned insert count.
& $python .\scripts\import_sqlite_to_postgres.py --source $source
if ($LASTEXITCODE -ne 0) { throw 'Importer preflight failed.' }

# Writes source data. Requires explicit approval after reviewing the preflight.
& $python .\scripts\import_sqlite_to_postgres.py --source $source --apply
if ($LASTEXITCODE -ne 0) { throw 'Data import failed; resolve the reported conflict and rerun safely.' }

# Read-only final validation; safe to rerun after a stopped import.
& $python .\scripts\import_sqlite_to_postgres.py --source $source --validate-only
if ($LASTEXITCODE -ne 0) { throw 'Post-import validation failed.' }
```

The commands above are documentation only; none were run against Neon.
`alembic upgrade head` is a schema-changing operation. Do not run it or deploy
the Render Blueprint until the schema and import plan have been approved.

If any run reports a conflicting primary or unique key, stop and investigate
the existing target row. Do not delete or update it to force the import.
Resolve the conflict through a separately approved data-reconciliation plan,
then rerun the importer. It will not silently merge accounts or change IDs.

## Local tests

The importer tests create temporary SQLite source and target databases,
initialize them with the local Alembic migrations, and test import, rerun,
validation, conflict protection, and backup verification. They do not connect
to Neon or use either real SQLite dataset.
