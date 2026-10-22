# MCP server (hakomcp)

`hakomcp` (currently `0.2.0`) is a [Model Context Protocol](https://modelcontextprotocol.io) server over stdio. It opens one local HakoDB database and gives an agent a task-level control plane for documents, queries, indexes, change observation, maintenance jobs, and engine-native sync.

It is not a replacement for `hakocli`. `hakocli` is the debugging and operations CLI for humans and scripts. `hakomcp` is the long-lived process an agent talks to. Replication stays in the HakoDB engine: MCP starts and observes sync, it does not relay documents itself.

## Requirements

- Rust stable to build from source.
- `hakodb 0.16+`.
- MCP protocol version `2024-11-05`.

```sh
cargo build --release
# binary: target/release/hakomcp
```

`net-sync` and `cloud-sync` are Cargo features and are enabled by default. `cargo build --release --no-default-features` produces a local-only binary with no network listeners.

## Run

```sh
hakomcp --db ./my-data --profile data
```

| Flag | Meaning |
|---|---|
| `--db PATH` | Database directory (default `./hakomcp-data`). |
| `--profile read\|data\|sync\|admin` | Capability profile (default `data`). |
| `--allow-network` | Allow sync listeners. Required by `--profile sync`. |
| `--allow-destructive` | Allow real `documents_delete_where` deletion. |
| `--subscribe-to LIST` | Collection allowlist for change notifications and watches. |
| `--collection-allow LIST` | Only these collections are visible; trailing `*` is supported. |
| `--collection-deny LIST` | Hide these collections; trailing `*` is supported. |
| `--max-query-rows N` | Hard cap on query rows and vector `k` (default `1000`). |
| `--max-result-bytes N` | Hard cap on one tool result or resource (default `1048576`). |
| `--log-format text\|json` | Stderr log format (default `text`). |

The process speaks newline-delimited JSON-RPC on stdin/stdout. Logs go to stderr; stdout carries protocol messages only. A client must call `initialize` before tools or resources.

Example MCP client entry:

```json
{
  "mcpServers": {
    "hako": {
      "command": "hakomcp",
      "args": ["--db", "/absolute/path/to/my-data", "--profile", "data"]
    }
  }
}
```

## Profiles

Tools outside the active profile are absent from `tools/list` and rejected at call time.

| Profile | Adds |
|---|---|
| `read` | Reads, queries, aggregates, query plans, indexes, stats, watches, jobs inspection. |
| `data` | Everything in `read`, plus document writes, batches, index creation, and schema changes. |
| `sync` | Everything in `data`, plus sync start/stop/status. Requires `--allow-network`. |
| `admin` | Everything, plus destructive deletes, compaction, vacuum, flush, and job cancellation. |

Use `read` for retrieval agents, `data` for application agents, `sync` for a node controller, and `admin` only for trusted operators.

## Tools

Canonical names are listed below. The original aliases `get`, `put`, `query`, `create_index`, `find_near`, and `find_paths` still work but are not listed.

### Documents and collections

| Tool | Arguments | Result |
|---|---|---|
| `document_get` | `collection`, `id` | `{found, document}` |
| `document_put` | `collection`, `doc`, `id?`, `vectors?` | `{ok, collection, id}` |
| `document_patch` | `collection`, `id`, `updates` | `{ok, collection, id}` |
| `document_delete` | `collection`, `id` | `{ok, collection, id}` |
| `document_batch` | `mutations` | `{ok, count, ids}` |
| `collection_list` | - | collections with counts |
| `collection_describe` | `collection` | fields, schema, and counts |
| `collection_stats` | `collection` | engine collection statistics |
| `schema_set` | `collection`, `schema` | `{ok, collection}` |
| `schema_clear` | `collection` | `{ok, collection}` |

`mutations` is an array of `{op: "put", collection, id?, doc}`, `{op: "patch", collection, id, updates}`, or `{op: "delete", collection, id}`. A batch is atomic.

A vector field is binary LE `f32[]` in the engine, which JSON cannot express directly. `vectors` takes a map of field to number array and encodes it; entries override same-named `doc` fields.

```json
{
  "name": "document_put",
  "arguments": {
    "collection": "products",
    "id": "kopi-1",
    "doc": { "name": "Kopi", "category": "drink" },
    "vectors": { "embedding": [0.12, -0.03, 0.88] }
  }
}
```

### Query and indexes

| Tool | Arguments | Result |
|---|---|---|
| `query` | `collection`, `filters?`, `any?`, `elem_match?`, `order_by?`, `limit?`, `offset?`, `select?`, `cursor?` | `{collection, count, documents, next_cursor?}` |
| `aggregate` | `collection`, `op`, `field?`, filters | `{results}` |
| `explain` | `collection`, filters | `{collection, plan}` |
| `index_create` | `collection`, `kind`, `field?`, `dim?`, `metric?`, `fields?` | `{ok, ...}` |
| `index_list` | `collection?` | indexes by kind |
| `find_near` | `collection`, `field`, `vector`, `k?` | nearest-first hits with `score` |
| `find_paths` | `collection`, `id`, `direction?`, `edge_field?`, `max_depth?`, `limit?`, `via_edge?`, `weight_field?` | traversal hits |

`kind` is `secondary`, `fts`, `vector`, `composite`, `edge`, or `traverse`. Vector indexes need `dim`; `metric` is `cosine` (default) or `l2`. The engine backfills existing documents when an index is created.

`filters` are AND-combined and `any` entries are OR-combined. Each filter is `{field, op, value}` with `op` one of `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `match`, `match_prefix`, `contains`, `starts_with`, `in`, `array_contains`, `array_contains_any`, `array_all_eq`, `not_in`. `order_by` entries are `{field, direction}`. `limit` defaults to 50.

Pagination is offset-backed: pass `cursor` from a previous `next_cursor`. The cursor is opaque to the client; do not parse it.

### Observation and jobs

| Tool | Arguments | Result |
|---|---|---|
| `watch_create` | `collection`, `filters?`, `any?`, `elem_match?` | `{id, uri}` |
| `watch_delete` | `id` | `{ok}` |
| `job_list` | - | recent jobs |
| `job_get` | `id` | job state and result |
| `job_cancel` | `id` | `{ok}` (admin only) |

Change notifications are opt-in. A collection must be in `--subscribe-to`; then subscribe to `hakodb://collections/<name>` and the server sends coalesced `notifications/resources/updated` messages. `watch_create` adds a filtered watch and reports matches on `hakodb://watches/<id>`. Remote sync writes also trigger notifications only for subscribed collections.

Jobs and sync are pull-only in this release. Poll `job_get` or read the job resources; do not wait for a job notification.

### Maintenance and destructive work

| Tool | Profile | Arguments |
|---|---|---|
| `compact` | `admin` | - |
| `vacuum` | `admin` | - |
| `flush` | `admin` | - |
| `documents_delete_where` | `admin` | `collection`, filters, `dry_run` (boolean) |
| `server_status` | all | - |

Always call `documents_delete_where` with `"dry_run": true` first. A real deletion requires both `"dry_run": false` and `--allow-destructive`; it runs as a job.

### Sync

| Tool | Arguments | Result |
|---|---|---|
| `sync_start` | `mode`, `node_id`, `room`, plus mode arguments | `{ok, mode, ...}` |
| `sync_stop` | - | `{ok, active}` |
| `sync_status` | - | redacted status |
| `sync_peers` | - | peer identities and dial state |
| `sync_versions` | - | per-collection version map |

Sync tools need `--profile sync` or `--profile admin`, plus `--allow-network`. One controller may run per process; call `sync_stop` before starting another.

## Resources

| URI | Contents |
|---|---|
| `hakodb://collections/<name>` | Collection sample: count and up to 100 documents. |
| `hakodb://collections/<name>/schema` | Collection schema, or `null`. |
| `hakodb://collections/<name>/indexes` | Index definitions for the collection. |
| `hakodb://collections/<name>/stats` | Engine collection statistics. |
| `hakodb://server/status` | Version, profile, limits, subscriptions, watches, jobs, sync state. |
| `hakodb://server/jobs` | Recent jobs. |
| `hakodb://server/jobs/<id>` | One job. |
| `hakodb://watches/<id>` | One watch and its match count. |
| `hakodb://sync/status` | Redacted sync status (sync/admin profiles only). |
| `hakodb://sync/peers` | Peers and mesh dial state (sync/admin profiles only). |
| `hakodb://sync/versions` | Version map, filtered by collection policy (sync/admin profiles only). |

Collection resources honor `--collection-allow`, `--collection-deny`, and `--max-result-bytes`.

## Sync topology

`sync_start` supports three modes:

| Mode | Arguments | Engine role |
|---|---|---|
| `mesh` | `port`, `static_peers?`, `discovery?`, `relay?` | Peer-to-peer mesh node. |
| `cloud_server` | `bind`, `max_clients?` | Cloud room server. |
| `cloud_client` | `server_url` | Cloud room client. |

`discovery` is `mdns` (default), `broadcast`, `both`, or `off`. With `off`, only `static_peers` are dialed; this is the recommended mode for containers and locked-down hosts. `max_clients` is a per-room cap; `0` means unlimited.

Secrets never appear in tool arguments. Set them in the server environment:

| Variable | Use |
|---|---|
| `HAKOMCP_SYNC_ROOM_KEY` | Mesh and cloud room key. Required for every sync mode. |
| `HAKOMCP_CLOUD_AUTH_TOKEN` | Cloud server/client auth token. Required for cloud modes. |
| `HAKOMCP_CLOUD_API_KEY` | Optional cloud client group API key. |

The process that starts sync owns the controller. A typical two-node mesh uses one static peer so only one side dials:

```json
{
  "name": "sync_start",
  "arguments": {
    "mode": "mesh",
    "node_id": "node-a",
    "room": "production",
    "port": 7401,
    "static_peers": ["10.0.0.12:7401"],
    "discovery": "off"
  }
}
```

`sync_status` and `hakodb://sync/status` never expose the room key, auth token, or API key. The cloud status object is rebuilt field by field; the engine's `room_key` field is never serialized.

A minimal cloud pair:

```json
{ "name": "sync_start", "arguments": {
  "mode": "cloud_server", "node_id": "server", "room": "production",
  "bind": "0.0.0.0:7401", "max_clients": 64
} }
```

```json
{ "name": "sync_start", "arguments": {
  "mode": "cloud_client", "node_id": "client", "room": "production",
  "server_url": "ws://10.0.0.12:7401"
} }
```

## Security boundaries

- The MCP transport is local stdio. There is no MCP listener. Remote agents need a separate transport or routing layer in front of stdio.
- Profiles are least privilege. A tool hidden by the profile is also rejected by name.
- `--collection-allow` and `--collection-deny` hide collections from tools, resources, samples, and the sync version map.
- `--max-query-rows` and `--max-result-bytes` bound query work and one response. The stdio channels are bounded, so a slow client applies backpressure instead of growing memory.
- Destructive work needs the `admin` profile and, for real deletes, `--allow-destructive`.
- Sync needs the `sync` or `admin` profile and `--allow-network`. Secrets come from the environment, never from MCP messages or logs.
- Do not run `admin` or `sync` for an untrusted agent. Use `read` or `data` and a collection allowlist.

## Persistence and recovery

HakoDB writes through its WAL. A hard kill after a successful write is recovered on the next open; integration tests cover this. Durability is the engine's contract, not MCP's.

Backup and restore are deliberately outside `hakomcp`. Use `hakocli` or your operator tooling while the database is offline.

## Compatibility

| `hakomcp` | `hakodb` | MCP protocol | Rust |
|---|---|---|---|
| `0.2.x` | `0.16.x` | `2024-11-05` | stable |
| `0.1.x` | `0.16.x` | `2024-11-05` | stable |

The six original tools and the `hakodb://collections/<name>` resource shape stay compatible through `0.x`.

## Performance

`hakomcp` is a control plane, not a high-QPS application driver. Each tool call is a full JSON-RPC round trip over stdio, and each result is capped by `--max-result-bytes`. For bulk ingestion, use `document_batch`; for large scans, paginate and project fields with `select`. Measure your own workload before setting the caps.
