# Cluster (one box, many instances)

`hakocluster` (`hakodb/hakocluster`, currently `0.3.11`) is an in-process dispatcher over N `hakodb` instances on one machine: reads fan out, writes route to one writer, and `socket_sync` keeps replicas identical. It is the backend-side companion to [socket sync](sync-socket.md): the dispatcher is the single writer the socket plane assumes.

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
- **Read Fan-out.** `read_counts` / `read_index` show distribution; routing is per call, not sticky.
- **Engines: Hako only.** Members are Hako data dirs (`DbSpec.paths`). SQLite, Postgres, and friends are *backend drivers*, not cluster members — the cluster never opens them. Mixing engines in one deployment happens at the backend layer (`driver = "sqlite"` next to a `hakocluster` database), never inside one cluster.

## Multidatabase: named clusters in one process

`Databases` holds N named clusters behind exact-name lookup — no default database (a silent default would route writes somewhere the operator didn't choose):

```rust,ignore
let dbs = Databases::open(vec![
    DbSpec { name: "billing".into(), paths: vec!["/data/b1".into()], config: ClusterConfig::default() },
    DbSpec { name: "analytics".into(), paths: vec!["/data/a1".into(), "/data/a2".into()], config: ClusterConfig::default() },
], "/run/hc".into())?;
let billing = dbs.get("billing").expect("unknown name 404s");
dbs.names()  // ["billing", "analytics"], declaration order
```

Rules: each database meshes under `sock_root/{name}` (the mesh boundary — no cross-database peering is representable); bad/duplicate/empty declarations, or any per-db open failure, refuse the whole registry; one shared tokio runtime, never one per database. C ABI: `hk_databases_open(config_json)` (same shape: `sock_root` + `databases[]`), `hk_db_get` (fresh `HK_Cluster` handle over the same cluster), `hk_databases_names`, `hk_databases_close`.

Note the layering: this registry is for embedding the cluster as a library. `hakobackend`'s `[databases]` is separate — each named backend database opens its *own* `ClusterDb` from its own dirs (see [Backend drivers](backend-drivers.md)); the two mechanisms compose but never share state.

## Relation to hakobackend

`hakobackend` embeds this pattern for multi-instance deployments: several backend processes hold identical data via socket sync while a balancer spreads HTTP load. If you run one backend process, you don't need the cluster — one `hakodb` with socket sync (or nothing) is enough.

## Multi-box composition (no new knobs)

The cluster has no cross-machine sync knobs — `ClusterConfig` carries durability, group-commit, stagger, lag guard, and `sock_dir` only, by design. Multi-box replication composes existing pieces instead of adding transport:

```
box A: cluster (writer + replicas, socket_sync)
box B: cluster (writer + replicas, socket_sync)
between boxes: net-sync mesh room OR cloud-sync hub, at hakodb level
```

Every cluster member is a full `Hako` instance, so each box joins the LAN/cloud plane like any single instance would. Within a box: socket snapshot + 500ms tail. Between boxes: mesh/cloud cadence. Echo interplay is already handled — replicated ingest inserts echo entries, so ops arriving from LAN are not rebroadcast back to LAN via the socket tailer, and vice versa.

Hard limit, state it plainly: **each box keeps its own writer** (promote is per-cluster; there is no cross-box election). Concurrent writes to the same document on two boxes converge by last-write-wins — one side wins silently. This pattern fits write-partitioned workloads (edge regions, tenant affinity), never shared counters or ledgers. If two boxes must coordinate one document, that document belongs on one box (or behind one backend).

## Tailer variant: N+1 with a dedicated bridge (issue #23)

When the operator wants the bridge managed (instead of hand-rolled per-box mesh/cloud), the cluster derives one extra member:

- Config declares N serving paths plus **one** of `tailer_mesh {name, room_key, port}` (needs cargo feature `tailer-mesh`) or `tailer_cloud` (needs `tailer-cloud`). Both set, or knob set without its feature, or any tailer off-unix: fail-closed boot error.
- The tailer gets a derived sibling dir (`<first-dir>.tailer`), meshes locally like every member, then bridges outward. It never serves fan-out reads, is never promotable, and is always read-only.
- Same LWW-across-boxes rule as the manual pattern; same single-writer-per-box. C ABI: `tailer_mesh` / `tailer_cloud` objects in the open config JSON (malformed shapes fail parse).

### Cloud tailer: client or server

`tailer_cloud` carries an explicit `mode` — no default (a silent default would point the bridge somewhere unintended):

- `mode: "client"` + `room_name`/`room_key`/`server_url`: join someone's hub (edge box calling home).
- `mode: "server"` + `bind_addr` (e.g. `"0.0.0.0:8080"`): host a room for other boxes' tailer-clients (regional hub). The server is room-agnostic by design, so `room_*` keys in server mode are refused, not ignored.

Either side is still just a bridge: remote writes land via sync ingest (which bypasses the read-only flag by design, like all replicated ingest) and fan out locally over the socket tail. Writer-per-box and LWW still apply — a tailer-server does not make two boxes agree on one document.

## Common mistakes

- **Clustering across machines.** Instances must share a box (unix sockets). Across boxes, run one backend per box with [cloud sync](sync-cloud.md) between them.
- **Two writers during failover.** Promote first, route second. The epoch log exists so you can verify the rotation happened once.
- **Expecting cross-instance transactions.** Transactions stay per-instance (see [Batches and transactions](transactions.md)); the cluster routes, it doesn't coordinate.
