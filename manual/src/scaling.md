# Scaling cloud sync

A cloud-sync deployment can serve reads and cold catch-up from more than one process. The supported shape is **one writer room plus any number of read-only replicas**, kept identical by engine mesh sync. Clients may connect to any pod for sync sessions; writes must reach the writer.

```
            ┌── clients ── LB/router ──┐
            ▼                          ▼
 pod A (writer)           pod B (replica)        pod C (replica)
 hakocloudserver          hakocloudserver        hakocloudserver
  └ hakodb engine          └ engine (read-only)   └ engine (read-only)
      sync :8411               sync :8412             sync :8413
      mesh :9101 ──────────────▲ dialer B─────────────▲ dialer C
               net_sync WAL tail (mesh, TCP)
```

## Topology

- Every pod declares the same room (`name`, `key`, `token`).
- Only the writer runs a writable engine.
- Writes land on the writer; its engine WAL tail broadcasts over the engine mesh (`net_sync`) to every replica.
- Reads and cold catch-up are served by any pod from its local engine and local cache.
- Replicas may receive a paged bootstrap from the writer when they join or fall behind.

This is a one-writer topology. There is no automatic failover; promotion is operator-driven.

## Writer configuration

```toml
server_id = "hako-writer-0"
rooms_dir = "./wrooms"
admin_bind = "0.0.0.0:8301"

[[rooms]]
name = "g35"
key = "k-mesh"
token = "t-mesh"
sync_bind = "0.0.0.0:8311"
mesh_bind = "0.0.0.0:9101"   # replicas dial this
```

## Replica configuration

```toml
server_id = "hako-replica-0"
rooms_dir = "./rrooms"
admin_bind = "0.0.0.0:8302"

[[rooms]]
name = "g35"
key = "k-mesh"
token = "t-mesh"
sync_bind = "0.0.0.0:8312"
mesh_peers = ["tcp://hako-writer-0.hako-svc:9101"]
read_only = true
```

Validation is fail-closed:

- Every pod needs a distinct `server_id`. The mesh node id is `<server_id>-<room>-<role>`; duplicate ids collide in the writer's peer map, so replicas evict each other's connections.
- `read_only = true` without `mesh_peers` refuses to boot.
- A read-only room may not declare `mesh_bind`; replicas dial, they are not dial targets.
- Every peer address is parsed at boot, so a typo fails loudly instead of leaving an empty room.

Rooms that declare neither `mesh_bind` nor `mesh_peers` behave as a single hub pod.

## Kubernetes mapping

- **Deployment**: one pod per serve point. A fresh replica pulls the writer engine over mesh bootstrap, so a wiped `rooms/` self-heals; use an ephemeral volume if faster starts matter.
- **Services**: `hako-writer` for writer pods and `hako-replica` for replicas. Route write sessions to the writer Service; sync sessions may go to either.
- **Boot wiring**: peer addresses use the writer's stable Service DNS, for example `hako-writer-0.hako-svc:9101`.
- **Probes**: `/api/health` lists rooms. Add an application-level readiness check for the mesh peer status where the deployment needs it.

## Manual failover

1. Stop the old writer.
2. Change one replica to writer form: `read_only = false` and `mesh_bind = ...`.
3. Restart that pod and confirm it is healthy.
4. Start the old writer as a read-only replica pointed at the new writer's mesh address.

The demoted writer keeps its WAL. On connect it bootstraps from the new writer, applies newer writes and tombstones, and converges. Give every pod a distinct `server_id`. Clients reconnect through their Service route and re-sync from the current state. Engine epoch and last-write-timestamp semantics keep ordering consistent.

## Operational notes

- Dial retries run on a 15-second cadence per peer address; connection outcomes are logged.
- Replica reads can be stale because mesh replication is asynchronous. Clients converge on the next sync cycle; this is the tradeoff for write-once, read-everywhere.
- Read-only replicas only ingest. They do not serve a bootstrap snapshot or fan out their own WAL. A demoted writer still holds a full snapshot, and two simultaneous full sends can fill both socket buffers and deadlock the handshake.
- `sync_checkpoint` is a local write and is blocked on a read-only replica, so promotion starts at offset 0 and re-reads the WAL.
- `/api/compact` is a no-op below `auto_compaction_threshold_bytes` (8 MiB default). Compare document counts and query results, not WAL byte sizes.
- Treat a forced stop as a crash: promote only after the new writer is healthy, and keep the old writer stopped until it starts as a read-only replica.
- Multicast discovery (`mDNS`/broadcast) is off for mesh-wired rooms. Container networks do not carry it, and disabling it removes a failure class. Desktop LAN groups keep normal discovery; this mode is server-only.
- `net-sync` compiles out on non-desktop targets. The `hakocloudserver` Linux binary includes it.

## Limits

- Same-room active-active writes are not supported. Replication is strictly one-writer.
- Automatic failover and leader election are not provided.
- Many concurrent cold pulls still cost memory on each client. More serve points spread that cost; they do not remove it. For many LAN peers behind one cloud pull, use [LAN relay](lan-relay.md).
