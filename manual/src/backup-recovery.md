# Backup and recovery

## Backup

```rust
db.backup("./backups/2026-10-15")?;   // flushes, then snapshots to a directory
```

Rules:

- `backup()` flushes internally. A **manual file copy** needs `flush()` first — copying a live directory without flushing can capture a torn WAL tail.
- `compact()` before backup keeps snapshots small (dead versions purged).
- Back up the **whole directory** — segments, WAL, and index snapshots travel together. Index snapshots are a performance cache, not optional metadata: restorable without them, slower to warm.
- Encrypted databases back up encrypted. The backup is useless without the key, and the key must never travel with the backup.

## Recovery

Open runs recovery automatically: committed WAL ops replay, uncommitted tails are discarded, index snapshots verify and rebuild on mismatch. There is nothing to run manually.

After an unclean shutdown, expect the first `open` to take longer (replay + verify). If it fails, the error names the layer (WAL decode vs segment framing vs snapshot checksum) — report it with the full message; do not delete files to "fix" it.

## Common mistakes

- **Backing up individual files.** The directory is the unit. Cherry-picking `*.dat` without the WAL loses recent commits.
- **Restoring over a running database.** Stop the process, replace the directory, start. Live restores corrupt both copies.
- **`vacuum` confused with backup.** `vacuum_collection` purges tombstones to reclaim space — it is maintenance, not a safety copy.
