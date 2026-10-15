# Choosing a mode

HakoDB has one engine and three optional sync planes. Pick by answering one question: **where does the data need to be besides this process?**

| Answer | Mode | Feature flag |
|---|---|---|
| Nowhere. One process, one file. | Embedded | (none) |
| Other devices on the same LAN. | Mesh | `net-sync` |
| Phones/laptops converging through your server. | Cloud client + server | `cloud-sync` |
| Sibling processes on the same box (balancer). | Socket | `socket-sync` |
| Smaller binary, no sync at all. | Embedded core | `--no-default-features` |

```toml
[dependencies]
hakodb = { version = "0.15", features = ["cloud-sync"] }
```

Rules of thumb:

- Start embedded. Add sync when a second data holder exists, not before — every plane adds binary size and operational surface.
- Mesh fits networks you control (office, venue, factory floor). It discovers peers over mDNS; across VLANs or the internet, use cloud instead.
- Cloud fits offline-first products: clients read/write locally at full speed and converge through your hub. You operate the hub (or use `hakobackend`, which embeds it).
- Socket fits N processes on one box that must hold identical data (e.g. behind a balancer): snapshots on connect, live tail after.

Sync replicates **documents and index definitions**; derived state (HNSW graphs, backlink indexes) rebuilds locally on each node. See the sync chapters (batch 2) for rooms, versions, and the encryption posture.
