# Backend realtime, files, TTL

## Realtime: WS + SSE, same pipeline

Three lanes feed one per-subscription snapshot pipeline (first event wins, idempotent — no duplicates): gateway bus (committed writes emit after commit, zero DB cost), driver push (hako watch / rethinkdb changefeeds, shared per collection), and an always-on poller (one `list` per collection per 2s tick, heals external writes and missed events).

```js
const ws = new WebSocket("ws://localhost:3000/ws");
ws.send(JSON.stringify({ t: "subscribe", key: "u1", collection: "users" }));
// → { t: "ready", key } then { t: "change", key, kind: "add|change|remove", doc }
// SSE alternative: GET /api/stream/users (event: change, 15s keep-alive)
```

Rules: `List` gate at subscribe, `Get` per document; no initial burst (GET first, then subscribe). Snapshots cap at 5,000 docs; deliveries cap at 200/sub/sec (overflow resyncs). 100 subs/connection; messages >1MB close it.

## Managed files

Byte files on a local volume + metadata docs in an ordinary collection (policy, indexes, aliases apply unchanged). Off without `file_dir`.

- Upload: `POST /api/files/{coll}/{id}[/{field}]` (single, multipart `file` part) or `POST /api/files/{coll}` (batch, auto ids). Per-file cap (`file_max_mb`), MIME allowlist + magic-byte agreement.
- Download: `GET /api/files/{coll}/{id}[/{field}]` with ETag, single-range 206, 304 on match.
- Signed URLs: `GET ...?sign=<seconds>` mints `{url, exp}`; `?exp=&sig=` consumes anonymously (HMAC, needs `file_sign_secret`).
- Delete removes metadata; bytes are reclaimed by the sweeper. Metadata-without-bytes 404s loudly (repair signal, not a bug to hide).

## TTL + unique + coalescing

- **TTL**: numeric `__ttl_at` (microsecond epoch). Expired docs read as missing everywhere; a 5-minute sweeper deletes them (100/collection/pass). No field = immortal.
- **Unique**: `create_index` with `unique:true` (simple single-field); enforced natively on SQL, via shadow docs in one serializable tx on hako.
- **Coalescing** (opt-in `--coalesce-writes`): eligible PATCH bodies merge per doc over 100ms; one stored write per window. Ato­mic PATCHes bypass. Acks happen at merge time — SIGKILL can lose one window.

## Common mistakes

- **Subscribing before the initial GET.** You will either miss the burst or double-render it. GET, render, then subscribe.
- **Uploading without `file_dir` and debugging 503s.** The 503 means "files off" — set the directory.
- **Treating signed URLs as permanent.** They expire by construction; mint per render, not per upload.
