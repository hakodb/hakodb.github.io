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

## Common mistakes

- **Expecting `put` to fail on existing ids.** It overwrites. Read-then-write races across threads need [transactions](transactions.md), not `put`.
- **Storing the id only inside the document.** Key lookups use the key argument; keep them consistent.
- **Deleting to "reset" test state.** Deletes tombstone; use a fresh directory for tests instead of deleting thousands of docs.
