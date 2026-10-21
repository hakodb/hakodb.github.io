# LAN relay for cloud sync

A LAN relay gives a room one cloud connection per LAN instead of one per device. One node runs both sync planes; the other LAN peers use mesh sync only and never dial the hub.

## Topology

- **Relay node**: runs a cloud-sync client to the hub room and a mesh server for the LAN.
- **LAN peers**: join the same room over mesh only.
- **Writes**: mesh-absorbed writes become part of the relay's WAL and reach the cloud through its normal push.
- **Reads**: every peer reads locally; cloud catch-up is served through the relay.

Configure the relay with both a cloud client room and a mesh listener. Configure the remaining peers with mesh peers only. See [Cloud sync](sync-cloud.md) and [Mesh sync](sync-mesh.md) for the plane-specific settings.

## Failure behavior

The relay is a single cloud path for the LAN. If it is down, the LAN has no cloud connection until another node takes the relay role. Moving the role is a configuration change and a restart; there is no automatic election.

Only one relay should be active per LAN and room. If two nodes dial the hub at the same time, both are independent cloud clients and the hub sees duplicate sessions.

## Admission control

The hub can cap distinct connected clients per room:

```rust
CloudSync::set_max_clients_per_room(n); // 0 = unlimited
```

- A client reconnecting with its own id re-admits and replaces its stale entry. The cap counts distinct clients, not retries.
- A new client beyond the cap receives `AuthResult { success: false, error: "room at capacity" }` and retries with backoff.
- Mesh-only LAN peers are unaffected because they never dial.
- The cap can be changed at runtime on shared handles, including FFI and SDK handles.

## Monitoring freshness

```rust
hakodb::cloud_sync::cloud_last_exchange_millis() -> Option<i64>
```

Returns the millisecond epoch of the last successful cloud exchange on any client face in the process: an auth round-trip or any decoded server packet. `None` means the process has never reached the cloud. Alert when `now - value` exceeds the freshness budget for the deployment.

## Limits

- The relay does not provide automatic leader election or failover.
- Cloud catch-up is shared, but each peer still materializes its own local database.
- The relay must be reachable by every LAN peer over the mesh plane.
