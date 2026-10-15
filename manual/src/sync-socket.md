# Socket sync (one box)

Feature: `socket-sync` (Unix only; a silent no-op on Windows so cross-platform builds stay green). Co-located instances on one machine hold byte-identical data over unix sockets — built for N processes behind a balancer with a single writer.

```rust,ignore
use hakodb::socket_sync::SocketSync;

let sync = SocketSync::new(db.clone(), vec![]);  // + db.config.sync_excluded
sync.serve("/run/hako/main.sock")?;              // listen
sync.dial("/run/hako/peer.sock").await?;         // connect out
// ...
sync.stop();
```

How it differs from mesh/cloud, deliberately:

- **No discovery, no rooms, no relay.** Explicit paths; both sides exchange `Hello` versions, then full snapshots (LWW dedups), then a 500ms live tail.
- **Snapshots, not deltas, on connect.** Correct via LWW and simple to reason about; right-sized for co-located databases.
- Same shared machinery underneath (`sync_core`: echo discipline, replicated-batch ingest, index-def convergence) and same length-prefix framing with the fail-closed frame cap.

## When to use it

One box, several processes, one logical dataset: balancer workers, a writer + hot-standby readers, sidecar indexers. If the processes are on different machines, that is [mesh](sync-mesh.md) or [cloud](sync-cloud.md), not this.

## Common mistakes

- **Expecting it on Windows.** AF_UNIX in this plane is Unix-only. Cross-platform code should gate on `cfg(unix)` or pick mesh/cloud.
- **Multiple writers.** The design assumes a single writer; concurrent writers on two sockets converge by LWW, which silently drops one side's intent. Route writes through one process (see [Cluster](cluster.md)).
