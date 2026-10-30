# Backend overview

`hakobackend` (`hakodb/hakobackend`) is a universal HTTP gateway: one Axum server speaks a Firestore-compatible wire protocol while **plug-and-play database drivers** do the storage. No database — including HakoDB — is bound to the core; every engine is an addon behind one trait.

```
clients (browser / phone / CLI / SDK)
  → HTTP/WS (`HTTP_CONTRACT`) → auth chain → policy file → rate limits
  → driver trait → hako | hakocluster | sqlite | postgres | mysql | rethinkdb
```

The driver trait (`hakobackend_core::Database`: CRUD, identical list semantics, atomic transactions, watch channel) is the only thing the core knows about storage. `hako` is the default embedded driver; **`hakocluster` is a first-class driver too** — same trait, N Hako dirs behind one handle, capabilities delegated to its writer (see [Backend drivers](backend-drivers.md) and [Cluster](cluster.md)). Switching drivers is two config lines + `/api/admin/reload`, no rebuild.

Design rules that never bend:

- **One backend, one namespace.** Collection names pass through unchanged; policy is one global file. Multi-tenancy (if ever needed) lives outside.
- **Wire parity.** Whatever driver sits behind, clients observe identical behavior — enforced by a shared conformance suite every driver must pass.
- **Fail-closed.** Rule typos, unknown auth names, bad config: refuse at boot or reject the request. Never fail open. Without a policy file the server runs OPEN for development and logs WARN — never for production.

Repository map (full contracts live there): `HTTP_CONTRACT.md` (wire), `AUTH_CONTRACT.md` (providers), `DRIVER_CONTRACT.md` (addons), `SECURITY_RULES.md` (policy), `PERFORMANCE_NOTE.md` (numbers), `policy.standard.toml` + `hakobackend.example.toml` (copy-paste starters).
