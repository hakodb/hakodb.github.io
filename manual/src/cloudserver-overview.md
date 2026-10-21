# Cloud server overview

`hakocloudserver` (`hakodb/hakocloudserver`, currently `0.1.1`) is a standalone cloud-sync hub with an admin console: one process hosts N independent rooms, each with its own database and its own sync listener, plus one HTTP admin plane scoped to the room you log into.

```
devices (offline-first clients)
  → ws://hub:port-per-room (sync plane, one listener per room)
  → http://hub:admin-port (admin console: data, users, groups, events)
```

## Room model

A room is a sync group with its own database (`<rooms_dir>/<room_id>/`, opaque hash — never the plain name), its own hub secret, and its own sync listener port. Rooms never share a database handle, so data can never mix across rooms no matter what the sync plane does. There is no shared registry and no default room: an empty room list refuses to boot, and unknown rooms fail closed (400/404, never a silent fallback).

The sync protocol is [Cloud sync](sync-cloud.md): each listener is a single-room `CloudSync` server enforcing its room pair at handshake. Group admission policy (`__groups`, per room) and user accounts (`__users`, per room) are sync-excluded — they never replicate to clients.

## When to use it

- You need a central rendezvous for offline-first clients that rarely share a LAN.
- You want a human console over the same data (inspect, query, backup) without shipping database files around.
- Rooms map to trust boundaries: one room per team, site, or product — never one room for everything.

If you need an HTTP query tier for apps instead (auth chains, policies, multiple drivers), that is [Backend (hakobackend)](backend-overview.md): the cloud server is a sync hub with a console, not an application gateway. For single-box embedded sync without a hub, see [Socket sync](sync-socket.md); for LAN peer-to-peer, [Mesh sync](sync-mesh.md).
