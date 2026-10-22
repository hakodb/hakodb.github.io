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

## Index drops

Each index create has a matching drop. All return `0` on success (including an absent target — drops are idempotent) and `-1` with `hk_last_error()` on failure, such as a read-only engine.

| Function | Removes |
|---|---|
| `hk_engine_drop_simple_index(engine, collection, field)` | secondary index |
| `hk_engine_drop_fts_index(engine, collection, field)` | full-text index |
| `hk_engine_drop_vector_index(engine, collection, field)` | vector definition + graph |
| `hk_engine_drop_composite_index(engine, collection, id)` | composite index by id |
| `hk_engine_drop_traverse_index(engine, collection)` | incoming-edge tracking |
| `hk_engine_drop_edge_index(engine, collection)` | `_from`/`_to` indexes + tracking |

Composite ids come from `hk_engine_list_indexes`; an id owned by another collection is rejected instead of deleted. Document data is never touched.

## Cloud status redaction

`hk_cloud_sync_status` returns JSON without `room_key`, so it is safe to log or expose to an admin UI. Rust callers that need the key for trusted in-process use can still read `CloudStatus::room_key`; use `CloudSync::status_redacted()` for anything that leaves the process.

SDK maintainers: regenerated headers live next to the binaries (`target/<…>/hakodb.h`); release bundles carry the header from the build that produced them.
