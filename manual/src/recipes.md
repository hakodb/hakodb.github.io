# Real-product recipes

Copy-paste starting points, not frameworks. Each assumes the relevant SDK chapter above.

## Offline-first desktop (Tauri)

One `hakodb` file per user next to the app data dir; `cloud-sync` client to your hub; `watch_collection` driving the UI. Conflict policy: last-write-wins — so give each user ownership of their documents (user-id-prefixed collections) and keep shared documents coarse-grained.

```ts
// on launch: open, start sync, subscribe
await setDoc(doc(db, "meta", "device"), { lastSeen: Date.now() });
```

## CLI tool with a local database

`hakocli` for operations plus an embedded `hakodb` in the tool itself, or just shell out to the CLI for scripts. Durability `Manual` + explicit `flush()` after batch imports; `Interval` for interactive use.

## Web/mobile backend (hakobackend)

Thin clients talk HTTP/WS to `hakobackend`; the backend owns the files (policy rules per collection, auth provider of your choice). Never open the same directory from the backend and another process. Deploy: static musl binary + TOML + systemd; monitor `/api/ready`, disk space, and backup age.

## LAN collaboration (mesh)

Two or more full apps on one network, one room key per environment. Seed with `hakocli serve` for demos; production nodes run `net-sync` in-process. Firewall checklist lives in [Mesh sync](sync-mesh.md).

## Multi-instance HTTP (cluster + socket)

N backend processes on one box behind a balancer: `hakocluster` routes writes to one instance while `socket_sync` keeps replicas identical. See [Cluster](cluster.md). Across boxes, sync the backends with [cloud](sync-cloud.md) instead.

## Analytics reads

Composite indexes on filter+order fields, `select_fields` projections, cursor pagination, `await_quiescent()` after bulk loads in tests. For one-off exploration, the C++ harness pattern (`benchmark.cpp`) or `hakocli query` beats writing code.
