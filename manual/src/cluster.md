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

## Relation to hakobackend

`hakobackend` embeds this pattern for multi-instance deployments: several backend processes hold identical data via socket sync while a balancer spreads HTTP load. If you run one backend process, you don't need the cluster — one `hakodb` with socket sync (or nothing) is enough.

## Common mistakes

- **Clustering across machines.** Instances must share a box (unix sockets). Across boxes, run one backend per box with [cloud sync](sync-cloud.md) between them.
- **Two writers during failover.** Promote first, route second. The epoch log exists so you can verify the rotation happened once.
- **Expecting cross-instance transactions.** Transactions stay per-instance (see [Batches and transactions](transactions.md)); the cluster routes, it doesn't coordinate.
