# Indexes

Indexes are built asynchronously in the background: writes return immediately, and `is_indexes_ready()` / `await_quiescent()` tell you when a fresh index has caught up. Querying before readiness falls back to correct (slower) paths — never wrong answers.

```rust
use hakodb::index::composite::definition::SortDirection;

db.create_index("users", "tenant")?;                       // secondary B-Tree
db.create_composite_index("users", vec![
    ("tenant".into(), SortDirection::Asc),
    ("age".into(), SortDirection::Desc),
])?;                                                       // composite
db.create_fts_index("articles", "body")?;                   // full-text
db.list_indexes(Some("users"));                             // inspect
```

- **Secondary**: one field, equality (and range) lookups.
- **Composite**: field tuples, for multi-field filters and order+limit without sorting.
- **FTS**: token/prefix search over text fields.
- **Vector / graph**: their own chapters ([Vector](vector.md), [Graph](graph.md)) — same readiness contract.

Index snapshots persist across restarts; after compaction or recovery the engine rewrites them automatically.

## Common mistakes

- **Indexing everything.** Each index costs write amplification and memory. Index the fields in your hot `where` clauses; nothing else.
- **Reading your own writes and panicking.** A `put` followed instantly by a filtered query can briefly miss the index — the fallback sweep still finds the row. If you need strict freshness in tests, `await_quiescent()`.
- **Forgetting FTS is token-based.** Substring edge cases (`startsWith` vs token prefix) behave differently; check which one your query needs.
