# Sync concepts

All three planes replicate the same thing — **documents and index definitions** — with the same conflict rule: **last-write-wins (LWW)** by logical timestamp. Derived state (HNSW graphs, backlink indexes, edge secondaries) never travels; each node rebuilds it from replicated documents.

## Rooms

A room is a sync group: mesh peers join by `room_key`; cloud clients join by
`(room_name, room_key)`. Different keys = different rooms. The cloud
server is bound to exactly one room at construction and rejects anything
else at handshake; multi-room hosting is N server processes (or
`hakocluster` multidb, one cluster per room).

## Versions and deltas

Every collection carries a version (max logical timestamp). On connect, peers exchange version maps; the side that is ahead sends only the ops the other missed. A fresh node gets a snapshot; a returning node gets a delta. Both directions run independently — either side can be ahead on different collections.

## Echo suppression

An op ingested from a peer must not bounce back out. Each node keeps a small echo cache (op key + timestamp); matches are dropped on send. If you see duplicates, the cache key differs somewhere (usually a room-prefix mismatch) — not a second bug.

## Withheld, excluded, local-only

Three ways to keep a collection out of sync, strongest first:

- **Withheld** (`is_sync_withheld`, `__`-prefixed internals): never leaves the device, by rule.
- **Excluded** (`sync_excluded` config, `collection-local` in CLI): skips the room for this node, rejoins with `--off`.
- **Local-only** (`set_collection_local`): participates in nothing, including snapshots.

## Same-minor lockstep

Peers on different minor versions connect, but new protocol fields (index defs, traverse state) only converge between same-minor nodes. Mixed-version rooms keep syncing plaintext collections throughout an upgrade; encrypted rooms pause for old peers (see [Encryption posture](sync-encryption.md)).

## Common mistakes

- **Expecting transactions across nodes.** Transactions are per-process; cross-node convergence is LWW. Design write ownership so two nodes rarely edit the same document.
- **Reading your own write on another node instantly.** Deltas travel on tailer cadence (mesh/cloud) or 500ms (socket) — milliseconds, not zero. Tests should `await_quiescent()` or poll versions, not sleep fixed amounts.
- **Reusing one room key everywhere.** Rooms are isolation boundaries; separate environments and tenants get separate keys.
