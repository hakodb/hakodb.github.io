# Cloud sync (central hub)

Feature: `cloud-sync`. Offline-first clients converge through a central server over WebSockets + MessagePack. Clients read/write locally at full speed with zero connectivity; deltas sync when connected.

## Server

```rust,ignore
use hakodb::cloud_sync::CloudSync;

let server = CloudSync::server(db, "hub-01", "master-secret");
server.start("0.0.0.0:8080").await?;   // room-agnostic: hosts any room
```

The server is not bound to any room: it accepts any `(room_name, room_key)`, stores each room under its own prefix, and relays only within rooms. An ingress flusher micro-batches client writes (5ms / 512 ops); a WAL tailer broadcasts server-side writes to subscribers.

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

Auth: the client presents its token; the server enforces per-room on receipt and relay. Group API keys and user stores live in sync-excluded internal collections.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Client connects, room stays empty | Wrong `room_name`/`room_key` (a different empty room) | Match both exactly |
| Reconnect storms | Server unreachable + fixed retry cadence | Check URL/firewall; backoff lives in your supervisor, not the client |
| Hub sees plaintext you expected hidden | No E2E: hub routes on cleartext room keys by design | See [Encryption posture](sync-encryption.md) — operator visibility is out of scope for at-rest keys |
| Old client in a new room | Pre-capability peer treated as unverified | Upgrade it; plaintext rooms keep working meanwhile |

## Common mistakes

- **Treating the hub as a database you query.** The hub is a sync relay with storage, not a query engine. Query clients locally; use `hakobackend` if you need an HTTP query tier.
- **One hub secret for all trust levels.** Separate the hub auth token (who may connect) from room keys (who shares data).
