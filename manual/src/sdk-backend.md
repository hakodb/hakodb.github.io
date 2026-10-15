# HTTP backend (hakobackend)

`hakodb/hakobackend` (currently `0.9.0`) is the universal HTTP gateway: Axum server + plug-and-play database drivers (`hako` included), Firestore-compatible wire protocol, auth providers (local, Firebase, GitHub, OIDC, custom), collection policy rules, rate limits, file uploads, and realtime WebSocket/SSE streams. Use it when clients are browsers or phones that can't embed the engine.

Wire contract: `GET /api/health`, `GET /api/ready`, CRUD under `/api/collections/{path}`, `POST /api/indexes`, `GET /ws`, `GET /api/stream/{collection}`, `POST /api/files/…`. Full contract: `HTTP_CONTRACT.md` in the backend repo; auth: `AUTH_CONTRACT.md`; policy: `SECURITY_RULES.md` + `policy.standard.toml`.

TypeScript clients use `@hakodb/backend` (`hakodb/hakobackend-ts`):

```ts
import { hakobackend, Query } from "@hakodb/backend";

const rows = await hakobackend.getDocs(new Query(hakobackend.collection("users")));
await hakobackend.setDoc(hakobackend.doc("users", "1"), { name: "alice" });
```

Deploy shape (production): static musl binary from release assets, TOML config, systemd unit, data dir + backups. The two live deployments run exactly this (`:3005` config-managed, `:3000` systemd).

## Relation to the engine docs

The backend embeds `hakodb` — collections, queries, indexes, and sync rooms behave as documented here; the backend adds HTTP transport, auth, and multi-tenancy policy on top. For engine semantics, read the core chapters; for wire/policy/auth specifics, read the backend repo contracts.

## Common mistakes

- **Bypassing policy with direct engine access.** If the backend owns the files, nothing else should open them. One writer per directory, always.
- **Exposing `/api/ready` as health and nothing else.** `ready` means "serving"; pair it with disk-space and backup-age monitoring or you will discover full disks via user reports.
