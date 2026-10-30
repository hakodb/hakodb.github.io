# CRUD

```rust,ignore
use hakodb::document::hako_doc::HakoDoc;
use hakodb::document::value::Value;

// CREATE / REPLACE (upsert: same call creates or overwrites)
let mut doc = HakoDoc::default();
doc.insert("name", Value::String("alice".into()));
doc.insert("tags", Value::Array(vec![Value::String("admin".into())]));
db.put("users", "1", &doc)?;          // -> Result<String> (the doc id)

// READ (None = missing, never an error)
let maybe: Option<HakoDoc> = db.get("users", "1")?;

// PARTIAL UPDATE (only the listed fields change)
db.patch("users", "1", vec![("age".into(), Value::Int(31))])?;

// DELETE
db.delete("users", "1")?;

// SUBDOCUMENTS (hierarchical nesting under a collection)
db.put_subdocument("users", "1", "address", &addr_doc)?;
```

`put` returns the id so call sites can ignore or log it. `get` on a missing id returns `Ok(None)` — check for `None` instead of catching errors.

Nested documents are plain values; subcollections (`put_subdocument`) are separate namespaces for when you need to query children independently.

## Deleting

Deletes are soft by default: the engine leaves a tombstone and keeps the payload in a retention record (`__hako_softdel`), so an accidental delete can be undone while it is still queued for the sweeper.

```rust,ignore
// SOFT DELETE (default): restoreable until the sweeper purges the record
db.delete("users", "1")?;

// HARD DELETE: bypass retention entirely (vacuum/sync paths keep this shape)
db.delete_force("users", "1")?;

// UNDO: re-create the doc at a fresh version; consumes the retention record
db.restore("users", "1")?;

// INSPECT: what is still restoreable / what the next sweep will purge
let restoreable = db.restore_available(Some("users"))?; // None = every collection
let due = db.delete_queue(Some("users"))?;
let purged = db.sweep_now()?; // returns expired records purged now
```

Retention is configured on `HakoConfig`:

| Field | Meaning |
|---|---|
| `soft_delete_retention_secs` | How long a soft-deleted doc stays restoreable (0 disables retention; deletes degrade to tombstone-only) |
| `soft_delete_sweep_interval_secs` | Background sweeper cadence |
| `soft_delete_max_bytes` / `soft_delete_max_count` | Retention budget caps |

Batch deletes follow the same rule: `BatchMutation::SoftDelete` is the default shape, `BatchMutation::Delete` is the legacy hard delete kept for vacuum and sync paths.

## Common mistakes

- **Expecting `put` to fail on existing ids.** It overwrites. Read-then-write races across threads need [transactions](transactions.md), not `put`.
- **Storing the id only inside the document.** Key lookups use the key argument; keep them consistent.
- **Deleting to "reset" test state.** Deletes tombstone and keep a retention record; use a fresh directory for tests instead of deleting thousands of docs.
