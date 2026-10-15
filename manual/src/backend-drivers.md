# Backend drivers

Every database is an addon behind `hakobackend_core::Database`: `insert` (fills missing ids), `set` replace vs shallow merge, `delete` returns the previous doc, `get` missing = `Ok(None)`, identical `list` filter/order/limit semantics, atomic `run_transaction`, `subscribe` receiver (or an empty channel + `watch=false` so core polls).

| Driver | Crate | Watch | Transactions |
|---|---|---|---|
| `hako` | `hakobackend-db-hako` | push | yes (default, embedded, zero-setup) |
| `hakocluster` | `hakobackend-db-hakocluster` | yes (via writer) | yes (via writer) — N Hako dirs, comma-separated; N>1 unix-only; refuses `sync_serve`/`sync_peer` (meshes itself) |
| `sqlite` | `hakobackend-db-sqlite` | polling | yes (file/`:memory:`, FTS5) |
| `postgres` | `hakobackend-db-postgres` | polling | yes (pool, JSONB) |
| `mysql` | `hakobackend-db-mysql` | polling | yes (pool, JSON) |
| `rethinkdb` | `hakobackend-db-rethinkdb` | changefeed push | emulated (validate+apply+rollback) |

Switching is two config lines + `/api/admin/reload` — no rebuild:

```toml
driver = "postgres"
data = "postgres://user:pass@host/dbname"
```

Writing a driver: implement the trait + `capabilities()` (be honest about `watch`/`transactions`), a `driver.toml` manifest, and pass the shared conformance suite (`run_conformance_suite`: CRUD, all 9 filter operators, order+limit, replace/merge, delete-returns-prev, subscribe). Fail = not registrable. Registration is one workspace member + one `open_driver()` arm + one registry row — handlers, policy, and realtime never know which driver is in use.

Operator contract is 9 symbolic ops (`== != > < >= <= array-contains array-contains-any in`) + word aliases + cursors + `offset`. Extra HakoDB operators (`match`, `contains`, `startsWith`, `notIn`) are reserved, not contract — drivers must not expose them over the wire.

## Common mistakes

- **Assuming native semantics leak through.** They don't by contract — but `unique`, vector/graph, and archive moves are capability-gated per driver. Read the 400s; they name what's missing.
- **Expecting push realtime on polling drivers.** Polling is one shared `list` per collection per 2s tick — fine for dashboards, wrong for sub-second UX. Need push on SQL? That means change-capture infrastructure outside this backend.
