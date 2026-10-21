# Queries

```rust,ignore
use hakodb::query::query::Query;
use hakodb::document::value::Value;

let rows: Vec<(String, HakoDoc)> = db.query(
    Query::new("users")
        .where_eq("tenant", Value::String("acme".into()))
        .where_filter("age", Operator::Gte, Value::Int(18))
        .order_by("age", false)   // false = descending
        .limit(50),
)?;
```

Operators: `Eq Ne Gt Gte Lt Lte In NotIn ArrayContains ArrayContainsAny Match Contains StartsWith`. Combine groups with `or_where`; page with `offset` or cursor bounds (`start_at / start_after / end_at / end_before` — cursors stay valid under concurrent writes, offsets don't).

```rust,ignore
// projection: fetch only the fields you touch (zero-copy from mapped bytes)
let names = db.query(Query::new("users").select_fields(vec!["name".into()]))?;

// aggregates without materializing rows
let total = db.execute_aggregation(/* ... */)?;
```

`explain(query)` returns the chosen plan (scan type, index usage) — the first tool when a query is slow.

## How the planner thinks

1. An equality filter on an indexed field → index posting (fastest).
2. Otherwise the smallest available posting, then verify.
3. Otherwise a sweep with predicate pushdown (correct, slower).

You don't pick the strategy; you shape the odds: index the fields you filter on (see [Indexes](indexes.md)). Unindexed queries are never wrong, just slower.

For the measured planner behavior and open work, read the [query planner study](query-planner.md). For raw, borrowed, and paginated read paths, see [Reading data](reads.md); for aggregation stages, see [Pipelines](pipelines.md).

## Common mistakes

- **Deep `offset` pagination.** `offset(100000)` still walks 100k rows. Use cursor bounds for infinite scroll.
- **Filtering on unindexed fields in a hot loop, then blaming the engine.** Run `explain` first; add the index; re-run.
- **Assuming cross-type equality.** An `Int(1)` filter does not match a stored `String("1")` through exact-key index buckets — the engine falls back to a verified sweep for ambiguous classes, but keep stored types consistent.
