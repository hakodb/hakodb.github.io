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

## Common mistakes

- **Clustering across machines.** Instances must share a box (unix sockets). Across boxes, run one backend per box with [cloud sync](sync-cloud.md) between them.
- **Two writers during failover.** Promote first, route second. The epoch log exists so you can verify the rotation happened once.
- **Expecting cross-instance transactions.** Transactions stay per-instance (see [Batches and transactions](transactions.md)); the cluster routes, it doesn't coordinate.
