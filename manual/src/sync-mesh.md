# Mesh sync (LAN)

Feature: `net-sync`. Peer-to-peer replication over TCP on the local network, with mDNS discovery. No server, no accounts — whoever holds the room key syncs.

```rust
use hakodb::net_sync::NetSyncer;
use std::sync::Arc;

let syncer = NetSyncer::new(db.clone(), "node-1", "shared-room-secret", vec![]);
syncer.start(7070).await?;                    // listen + discover + mesh
let status = syncer.status();                 // peer count, known peers
syncer.stop();
```

How it works:

1. **Discovery**: mDNS announcements on the LAN (desktop) or UDP subnet broadcast (Android, which needs no multicast lock). New peers are dialed automatically; known addresses are retried every 15s.
2. **Handshake**: `Identify` (room hash check) + capability exchange (encryption fingerprints — see [Encryption posture](sync-encryption.md)).
3. **Converge**: version maps compared per collection; the ahead side sends deltas; `SyncRequest` triggers a full bootstrap for newcomers.
4. **Live**: WAL tailers stream new ops; relay fan-out covers multi-hop topologies.

Framing is length-prefix + bincode, fail-closed at a 256MB frame cap.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Peers never appear | mDNS blocked (VLAN, firewall, Docker bridge) | Same subnet; open UDP 5353; or seed addresses for direct dial |
| Connects but no data flows | Room key mismatch (different rooms, silently isolated) | Same key on every node |
| Android hears nothing | Doze / no foreground service; desktop in mDNS-only mode | Foreground service on Android; `Both` discovery on desktop for broadcast peers |
| Encrypted room stalled | Keyless/wrong-key/old peer in the room | Distribute the key; upgrade old peers |
| Screen-off stalls (mobile) | OS suspends sockets | Foreground service; this is the OS, not the engine |

## Common mistakes

- **Deploying mesh across the internet.** It is a LAN protocol. Across networks, run [cloud](sync-cloud.md) instead.
- **One room key for dev and prod on the same LAN.** They will happily merge into one room. Separate keys per environment.
