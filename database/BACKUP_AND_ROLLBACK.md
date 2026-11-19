# Backup, migration and rollback guide (Windows)

All new database objects come from three **additive, re-runnable** scripts in `database/migrations/`:

| Script | What it does |
|---|---|
| `06_additive_schema.sql` | Adds `ASSIGNMENT.quantity_allocated`, `ASSIGNMENT.people_housed`, `INCIDENT.coordinator_id`, `LOCATION.parent_location_id`, tables `INCIDENT_STATUS_AUDIT` and `NOTIFICATION` |
| `07_hierarchy_and_coordinator_data.sql` | Adds 16 hierarchy rows (India, 7 states, 8 districts), links your 8 original locations to their district, fills `coordinator_id` from `reported_by` |
| `08_advanced_routines.sql` | 2 functions, 2 procedures, 5 triggers, 1 view (replaces the no-op trigger `trg_critical_request_audit`) |

Nothing is dropped, no existing table is recreated, no existing row is deleted. **Do not re-run `01_schema.sql` on a database that has data - it starts with `DROP TABLE`.**

## 1. Apply (backup is automatic)
```powershell
# from the project root
powershell -ExecutionPolicy Bypass -File database\apply_migrations.ps1
```
It asks for an admin MySQL account (migrations need ALTER/CREATE), writes a backup to `database\backups\pre_migration_<timestamp>.sql`, then applies 06 -> 07 -> 08 and stops at the first error.

### Manual alternative
```powershell
mysqldump -u root -p --single-transaction --routines --triggers --events --result-file="database\backups\manual_backup.sql" crisislink_db
mysql -u root -p crisislink_db -e "source database/migrations/06_additive_schema.sql"
mysql -u root -p crisislink_db -e "source database/migrations/07_hierarchy_and_coordinator_data.sql"
mysql -u root -p crisislink_db -e "source database/migrations/08_advanced_routines.sql"
```
(Use `--result-file`, not `>`: Windows PowerShell 5.1 writes `>` output as UTF-16 and corrupts the dump.)

## 2. Roll back - option A (surgical): remove only what the migrations added
```powershell
mysqldump -u root -p --single-transaction --routines --triggers --events --result-file="database\backups\before_rollback.sql" crisislink_db
mysql -u root -p crisislink_db -e "source database/migrations/09_rollback_additive.sql"
```
Deletes only: the audit/notification tables and their rows, the 4 new columns, the 16 hierarchy rows, the new routines/triggers/view; restores the original placeholder trigger. All original rows are untouched. (Tested: after migrate + rollback the data and schema dumps were identical to the original.)

## 3. Roll back - option B (full restore from backup)
```powershell
mysql -u root -p -e "DROP DATABASE crisislink_db; CREATE DATABASE crisislink_db CHARACTER SET utf8mb4;"
mysql -u root -p crisislink_db -e "source database/backups/pre_migration_<timestamp>.sql"
```
This returns the database to exactly the state at backup time (anything entered afterwards is lost).

## 4. Verify
```sql
SELECT COUNT(*) FROM LOCATION;            -- 24 after migration, 8 after rollback
SHOW TRIGGERS;                            -- 9 after migration
SELECT * FROM vw_location_tree LIMIT 5;   -- exists only after migration
```
