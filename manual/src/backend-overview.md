# Backend overview

`hakobackend` (`hakodb/hakobackend`, currently `0.9.0`) is a universal HTTP gateway: one Axum server speaks a Firestore-compatible wire protocol while **plug-and-play database drivers** do the storage. No database — including HakoDB — is bound to the core; every engine is an addon behind one trait.

```
clients (browser / phone / CLI / SDK)
  → HTTP/WS (`HTTP_CONTRACT`) → auth chain → policy file → rate limits
  → driver trait → hako | sqlite | postgres | mysql | rethinkdb (…)
```

Design rules that never bend:

- **One backend, one namespace.** Collection names pass through unchanged; policy is one global file. Multi-tenancy (if ever needed) lives outside.
- **Wire parity.** Whatever driver sits behind, clients observe identical behavior — enforced by a shared conformance suite every driver must pass.
- **Fail-closed.** Rule typos, unknown auth names, bad config: refuse at boot or reject the request. Never fail open. Without a policy file the server runs OPEN for development and logs WARN — never for production.

Repository map (full contracts live there): `HTTP_CONTRACT.md` (wire), `AUTH_CONTRACT.md` (providers), `DRIVER_CONTRACT.md` (addons), `SECURITY_RULES.md` (policy), `PERFORMANCE_NOTE.md` (numbers), `policy.standard.toml` + `hakobackend.example.toml` (copy-paste starters).
