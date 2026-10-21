# Indexes

Indexes are built asynchronously in the background: writes return immediately, and `is_indexes_ready()` / `await_quiescent()` tell you when a fresh index has caught up. Querying before readiness falls back to correct (slower) paths — never wrong answers.

```rust,ignore
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

## Readiness and backfill

Opening a database starts index recovery in the background. Separately, creating a secondary, full-text, vector, or **non-unique** composite index registers the definition and then backfills it on a background thread. While a collection's backfill is in flight, the planner treats that collection's index-backed plans as not ready and falls back to `FullCollection`. Two lanes have their own rules: the id-order `SortedKeys` slice stays available because it is index-independent, and vector lanes ignore pending writes (the executor live-filters deleted ids) but still wait for backfills to finish.

- `is_indexes_ready()` covers open-time recovery only.
- `quiescence_status()` reports `index_backfills`, `pending_index_ops`, and blob/maintenance work.
- `await_quiescent(timeout)` waits for all of it, including the async index worker and backfills. Use it before benchmarks and tests.

A unique composite index is the exception: its backfill is synchronous. Creation scans the collection, builds the claim ledger, and rejects the index if existing duplicates exist; the admission gate is active when the call returns.

Writes also gate planning, but per collection: a pending index update in collection A makes A use `FullCollection` until its worker drains, while collection B keeps its index plans. The global `QuiescenceStatus.pending_index_ops` still counts every pending update.

## Dotted paths

Composite indexes accept dotted field paths. A path is limited to 16 segments; creation rejects empty segments (`a..b`, leading or trailing dots). At index time the fetcher descends through `Map` values only:

- A missing path, an empty segment, or descent into a non-`Map` value reads as **absent**.
- An array in the middle of a path reads as absent; array element matching is `elemMatch`, not dotted-path indexing.
- **Absent is not null.** `Value::Null` is a concrete value and can be indexed. `eq(null)` matches only an explicit null; an absent path does not match `eq`, `ne`, or any range operator.
- A type mismatch is fail-closed: it does not match. No numeric string coercion is implied by indexing.



### Missing fields, sparse, and dense

Non-unique indexes skip a document when any indexed field is missing; the `sparse` flag is inert for them. For a unique index:

- `sparse: true` also skips a document with a missing field.
- `sparse: false` (dense) materializes the missing field as `Value::Null` so the document still participates in uniqueness.

Non-scalar values (`Map`, `Array`, `Reference`, `BlobLink`) encode as tag-only keys and are never claimed by a unique index; uniqueness is defined over scalar tuples.

## Filtered (partial) indexes

A composite definition may carry a `FilterGroup`. Only the matching documents enter the tree. The planner may ride a filtered tree only when the query **implies** the definition predicate; otherwise it uses a full scan so non-indexed documents are not silently lost.

The planner uses a deliberately narrow rule:

- The definition filter must be `FilterLogic::And`.
- Every definition condition must be pinned by an AND filter in the query with exactly one of:
  - `Eq` with the same value, or
  - `In` with a one-element array containing that value.
- `Or` filters, ranges, `Ne`, and other operators are not treated as proof; they fall back to the full-scan lanes.

Extra query filters are allowed. A filtered unique index applies the filter before admission, so documents outside the predicate do not hold claims.

## Composite ranges

A composite index can serve one range operator (`gt/gte/lt/lte/ne`) after an equality prefix, for example index `(tenant, score)` with `tenant = "t2" AND score >= 50`. Extra filters are re-checked after the scan, and the lane does not claim filter or order satisfaction; `limit` still rides the executor's TopN.

## Unique indexes and tombstones

Uniqueness is enforced synchronously at write admission by the claim ledger, not by the asynchronously updated B-tree. The ledger is rebuildable from storage; WAL remains the durability source. A violation is `HakoError::UniqueViolation` and is not retryable.

The ledger keeps a `freed` set per unique index. It records distinct document ids whose claim was released (delete, tuple switch, or a release that raced the first fold) so a late recovery fold cannot resurrect a stale claim. Entries are removed when the document claims again. There is no periodic sweep, so the memory bound is the number of **distinct released document ids per unique index** and grows with churn.

## See also

- [Queries](queries.md) for explain, covering reads, and pagination.
- [Reading data](reads.md) for raw/view read paths.
- [Vector search](vector.md) and [Graph traversal](graph.md) for those index families.

## Common mistakes

- **Indexing everything.** Each index costs write amplification and memory. Index the fields in your hot `where` clauses; nothing else.
- **Reading your own writes and panicking.** A `put` followed instantly by a filtered query can briefly miss the index — the fallback sweep still finds the row. If a caller needs strict freshness, call `await_quiescent()`.
- **Forgetting FTS is token-based.** Substring edge cases (`startsWith` vs token prefix) behave differently; check which one your query needs.
