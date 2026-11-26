# C ABI reference

Every non-Rust SDK reaches the same engine through a flat C API (`hakodb.h` generated per target by the build — never checked in, never hand-edited). Opaque handles, integer status codes, JSON or binary payloads, `hk_last_error()` for the message.

Handle families:

| Handles | Cover |
|---|---|
| `HK_Engine` | open/free, CRUD, query, batch, transactions, watch, backup/compact, stats, audit |
| `HK_Doc` / `HK_Batch` / `HK_Query` | builders freed explicitly (`hk_doc_free`, …) |
| `HK_Config` | durability, encryption, audit, workers, memory, blob threshold, compression |
| `HK_Transaction` / `HK_ResultSet` / `HK_Watch` | staged tx, result iteration, live subscriptions |
| `HK_NetSyncer` / `HK_CloudSync` | mesh and cloud planes (feature-gated: absent from minimal builds) |

Conventions every binding follows:

- **Ownership is explicit.** Anything `_new` must be `_free`d. Strings returned to C are callee-allocated — free with `hk_string_free`.
- **Status codes, not exceptions.** `0` (or non-null handle) means success; anything else means call `hk_last_error()`.
- **Panics don't cross.** A bad call reports through `hk_last_error`; the process survives.
- **Sync functions exist only in full builds.** Minimal (`--no-default-features`) DLLs lack the sync symbols — linking against them fails at load time, loudly, by design.

## Query execution lanes

`hk_query_execute_ex(engine, query, cancel)` is the canonical executor. Pass a
null cancel handle for ordinary calls. Older execute entry points remain
available as compatibility wrappers and are advisory-deprecated; bindings
should move to the canonical symbol without removing the old declarations.

The execute functions are not interchangeable — they differ in what they
materialize:

| Family | Result | Use when |
|---|---|---|
| `hk_query_execute_ex` | JSON array string from decoded documents | canonical API calls |
| legacy `hk_query_execute` / `hk_query_execute_with_cancel` | same output, compatibility wrappers | advisory-deprecated; migrate to the canonical executor |
| `hk_query_execute_json` | JSON array string emitted from pinned bytes | JSON egress without owned documents |
| `hk_query_execute_to_handles` | borrowed `HK_Doc` handles | engine throughput; caller reads fields |
| `hk_query_execute_raw` | pinned storage bytes, no decode | index-satisfied filters/ordering |
| `hk_query_execute_aggregation` | JSON aggregate result | `count`/`sum`/`avg`/`min`/`max` |
| `hk_query_explain` | plan report, no rows | tuning, never throughput |

`hk_query_reset` reuses a handle. `hk_view_*` pulls typed fields from borrowed
bytes. For the full decision table, see `docs/ffi-query-lanes.md` in the core
repository. Benchmark comparisons must use the same lane: the native harness
times `execute_to_handles`, not a JSON serializer.

## Open, boot schema, drops, and filtered search

Seven symbols round out the write-path, schema, introspection, and search surface:

| Function | Behavior |
|---|---|
| `hk_engine_open_exclusive(path)` | open holding an advisory data-dir lock; a second writable holder gets null + `hk_last_error()` (plain `hk_engine_open` keeps caller-owned semantics) |
| `hk_engine_ensure_indexes(engine, schema_json)` | declare the whole boot schema (secondary/composite/fts/vector/tracked) in one idempotent call; identical re-declaration is a no-op, a conflicting one fails loudly |
| `hk_engine_drop_indexes(engine, collection)` | canonical schema reset: remove every index family for a collection in one call; documents are untouched |
| `hk_engine_effective_config(engine)` | one JSON object with durability, commit trigger, index defs, quiescence (including `is_quiescent`), and stats |
| `hk_engine_hybrid_search_filtered(…, filters_json)` | canonical hybrid text+vector search with admission filters before rank truncation; `null` = unfiltered |
| `hk_engine_find_near_scored_filtered(…, max_distance, filters_json)` | canonical scored KNN (raw distance, lower = better) with a distance cap (NaN/≤ 0 = none) and admission filters |
| `hk_engine_subgraph_json_projected(…, fields_json)` | seed-scoped subgraph export with a node-field keep-list; `null`/`[]` = full docs |

Unfiltered search variants and graph/path FFI versions before V4 remain available but are advisory-deprecated; bind to the filtered and V4 symbols for new integrations.

The headers are append-only, so older bindings keep compiling against newer libraries; calling a new symbol against an older runtime fails at load time, loudly.

## Index drops

`hk_engine_drop_indexes(engine, collection)` is the canonical reset: one call removes every index family declared for the collection. It returns `0` on success and is a no-op when there is nothing to drop. Document data is never touched.

The family-specific drops remain for advanced callers. All return `0` on success (including an absent target — drops are idempotent) and `-1` with `hk_last_error()` on failure, such as a read-only engine.

| Function | Removes |
|---|---|
| `hk_engine_drop_simple_index(engine, collection, field)` | secondary index |
| `hk_engine_drop_fts_index(engine, collection, field)` | full-text index |
| `hk_engine_drop_vector_index(engine, collection, field)` | vector definition + graph |
| `hk_engine_drop_composite_index(engine, collection, id)` | composite index by id |
| `hk_engine_drop_traverse_index(engine, collection)` | incoming-edge tracking |
| `hk_engine_drop_edge_index(engine, collection)` | `_from`/`_to` indexes + tracking |

Composite ids come from `hk_engine_list_indexes`; an id owned by another collection is rejected instead of deleted. Prefer `drop_indexes` unless you need to remove one family while keeping the others.

## Cloud status redaction

`hk_cloud_sync_status` returns JSON without `room_key`, so it is safe to log or expose to an admin UI. Rust callers that need the key for trusted in-process use can still read `CloudStatus::room_key`; use `CloudSync::status_redacted()` for anything that leaves the process.

SDK maintainers: regenerated headers live next to the binaries (`target/<…>/hakodb.h`); release bundles carry the header from the build that produced them.

Header generation is opt-in: build with `cargo build --features header` and the header lands at `target/<profile>/hakodb.h` (release/tag CI does this for every bundle). Rust applications that depend on hakodb compile zero header machinery — the cbindgen build-dependency is optional and stays off unless the feature is enabled. The manual override `HAKODB_SKIP_CBINDGEN=1` skips regeneration in header-enabled builds; set it per-invocation, not globally, or the build that should produce release headers stops doing so.
