# C ABI reference

Every non-Rust SDK reaches the same engine through a flat C API (179 functions, `hakodb.h` generated per target by the build — never checked in, never hand-edited). Opaque handles, integer status codes, JSON or binary payloads, `hk_last_error()` for the message.

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

SDK maintainers: regenerated headers live next to the binaries (`target/<…>/hakodb.h`); release bundles carry the header from the build that produced them.
