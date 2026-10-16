# Cluster

`hakocluster` (`hakodb/hakocluster`, currently `0.4.0`) is an in-process dispatcher over N `hakodb` instances sharing identical data (kept so by `socket_sync`): **reads fan out** across replicas, **writes route** to a single designated writer. Manual failover moves the writer (`promote` returns an epoch; re-promote is idempotent, and the fence stays the read-only flags). There is no automatic failover: promotion is always operator-driven.

Scope: cluster, mesh, and replica only. Members are Hako data dirs; other engines are out of scope.

Non-unix builds stay green: peering compiles out, so N > 1 fails closed and N = 1 works as a degenerate single-node cluster.

```rust,ignore
let cluster = Cluster::open(&["./node-a", "./node-b", "./node-c"])?;
// reads spread across instances; writes go to the current writer
cluster.put("users", "1", &doc)?;
let hits = cluster.query(q)?;
cluster.promote(1)?;   // manual rotation / failover by instance index
```

Concepts:

- **Writer + replicas.** One instance takes writes; the rest serve reads and converge over socket sync (snapshot on connect, live tail after).
- **Health and rotation.** `healthy_count` / `refresh_health` track liveness; `promote` moves the writer role with an epoch guard so two writers never split-brain a failover.
- **Read fan-out.** `read_counts` / `read_index` show distribution; routing is per call, not sticky.

## Multidatabase: named clusters in one process

`Databases` holds N named clusters behind exact-name lookup — no default database (a silent default would route writes somewhere the operator didn't choose):

```rust,ignore
let dbs = Databases::open(vec![
    DbSpec { name: "billing".into(), paths: vec!["/data/b1".into()], config: ClusterConfig::default() },
    DbSpec { name: "analytics".into(), paths: vec!["/data/a1".into(), "/data/a2".into()], config: ClusterConfig::default() },
], "/run/hc".into())?;
let billing = dbs.get("billing").expect("unknown name");
```

Rules: each database meshes under `sock_root/{name}` (the mesh boundary — no cross-database peering is representable); bad/duplicate/empty declarations, or any per-db open failure, refuse the whole registry; one shared tokio runtime, never one per database. C ABI: `hk_databases_open(config_json)` (same shape: `sock_root` + `databases[]`), `hk_db_get` (fresh `HK_Cluster` handle over the same cluster), `hk_databases_names`, `hk_databases_close`.

## Multi-box: N+1 with a dedicated bridge

A cluster can derive one extra (+1) member whose only extra job is bridging outward, so serving members never touch cross-box latency:

- Config declares N serving paths plus **one** of `tailer_mesh {name, room_key, port}` (needs cargo feature `tailer-mesh`) or `tailer_cloud` (needs `tailer-cloud`). Both set, or knob set without its feature, or any tailer off-unix: fail-closed boot error.
- The tailer gets a derived sibling dir (`<first-dir>.tailer`), meshes locally like every member, then bridges outward. It never serves fan-out reads, is never promotable, and is always read-only.
- Same last-write-wins rule across boxes; same single-writer-per-box. C ABI: `tailer_mesh` / `tailer_cloud` objects in the open config JSON (malformed shapes fail parse).

### Cloud tailer: client or server

`tailer_cloud` carries an explicit `mode` — no default (a silent default would point the bridge somewhere unintended):

- `mode: "client"` + `room_name`/`room_key`/`server_url`: join someone's hub (edge box calling home).
- `mode: "server"` + `room_name`/`room_key`/`bind_addr` (e.g. `"0.0.0.0:8080"`): host this box's room for other boxes' tailer-clients. Works because single-room servers store plain names — the box-local dataset IS the room's data, so broadcast serves it directly.

Either side is still just a bridge: remote writes land via sync ingest (which bypasses the read-only flag by design, like all replicated ingest) and fan out locally over the socket tail. Writer-per-box and LWW still apply.

Hard limit, stated plainly: **each box keeps its own writer** (promote is per-cluster; there is no cross-box election). Concurrent writes to the same document on two boxes converge by last-write-wins — one side wins silently. This pattern fits write-partitioned workloads, never shared counters or ledgers.

## Common mistakes

- **Clustering across machines.** Instances must share a box (unix sockets). Converge across boxes with mesh or cloud sync instead.
- **Two writers during failover.** Promote first, route second. The epoch log exists so you can verify the rotation happened once.
- **Expecting cross-instance transactions.** Transactions stay per-instance (see [Batches and transactions](transactions.md)); the cluster routes, it doesn't coordinate.
