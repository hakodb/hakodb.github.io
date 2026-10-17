# Cloud sync (central hub)

Feature: `cloud-sync`. Offline-first clients converge through a central server over WebSockets + MessagePack. Clients read/write locally at full speed with zero connectivity; deltas sync when connected.

## Server

```rust,ignore
use hakodb::cloud_sync::CloudSync;

// Bound to exactly one room: serves only (game, secret-room-key).
let server = CloudSync::server(db, "hub-01", "master-secret", "game", "secret-room-key");
server.start("0.0.0.0:8080").await?;
```

The server stores collections under plain names and relays only within its room. An ingress flusher micro-batches client writes (5ms / 512 ops); a WAL tailer broadcasts server-side writes to subscribers. One server process = one room; multi-room hosting is N processes (or `hakocluster` multidb, one cluster per room).

For a batteries-included hub — N rooms per process, per-room databases, hub secrets, and a web admin console — run [hakocloudserver](cloudserver-overview.md) instead of hand-rolling `CloudSync::server`.

## Client

```rust,ignore
let client = CloudSync::client(
    db, "laptop-7", "game", "secret-room-key", "user-jwt",
);
client.start("wss://hub.example.com").await?;   // ws:// also works
// ... work offline or online, same API ...
client.stop();
```

On connect, both sides exchange `VersionPing` (versions + index defs, room-scoped) and the ahead side sends catch-up — symmetrical, so either side recovers missed deltas after downtime. `https://` URLs convert to `wss://` automatically (proxies, tunnels, ALBs all fine).

Catch-up is per-collection and strictly `>`, keyed on the collection version clock — not per document and not `>=`. A hub document written before a client joins replicates to that client normally, but if the *collection's* version clock happens to be identical on both sides (both at `1`, for example), neither side is "ahead" and nothing is pulled. Practical rule: if a fresh client must receive pre-existing hub data deterministically, write hub data so the hub's collection versions advance past the client's (e.g. after it joins), or give client-produced collections their own names instead of mirroring a hub-written collection name in opposite directions.

Auth: the client presents its token; the server enforces per-room on receipt and relay. Group API keys and user stores live in sync-excluded internal collections.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Client connects, room stays empty | Wrong `room_name`/`room_key` — the server rejects the handshake (fail-closed, nothing stored) | Match both exactly |
| Reconnect storms | Server unreachable + fixed retry cadence | Check URL/firewall; backoff lives in your supervisor, not the client |
| Hub sees plaintext you expected hidden | No E2E: hub routes on cleartext room keys by design | See [Encryption posture](sync-encryption.md) — operator visibility is out of scope for at-rest keys |
| Old client in a new room | Pre-capability peer treated as unverified | Upgrade it; plaintext rooms keep working meanwhile |

## Common mistakes

- **Treating the hub as a database you query.** The hub is a sync relay with storage, not a query engine. Query clients locally; use `hakobackend` if you need an HTTP query tier.
- **One hub secret for all trust levels.** Separate the hub auth token (who may connect) from room keys (who shares data).
