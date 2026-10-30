# CLI (hakocli)

`hakocli` is the command-line manager for any HakoDB database: document CRUD, queries, indexes, watch streams, and LAN/cloud sync management. It is the fastest way to inspect, seed, and operate a database file without writing code.

## Install

```sh
cargo install --path .
# or straight from GitHub:
cargo install --git https://github.com/hakodb/hakocli
```

Building from source: `cargo build --release`. The binary lands at `target/release/hakocli`. The `hakodb` dependency comes from crates.io; sync modes wire through the `net-sync` / `cloud-sync` cargo features (both on by default).

## Config file

`--config <file>` loads options from TOML. Precedence is always **CLI flag > config file > built-in default**, so a file can hold the stable base while one-off flags override it.

```toml
# hako.toml
db = "./demo.db"
durability = "on-commit"   # always | interval | manual | on-commit
# encryption_key = "secret"
# encrypted_cols = "users,tx"
time = true
count = false

[serve]
port = 7070
node_id = "node-1"
key = "room-key"
discovery = "both"         # mdns | broadcast | both
# bind = "0.0.0.0:8080"    # cloud server, or:
# server = "ws://127.0.0.1:8080"  # cloud client
# room_name = "game"
token = "s3cret"
```

```sh
hakocli --config hako.toml serve
hakocli --config hako.toml --db ./other.db query users --limit 5
```

`node_id` has no default: pass `--node-id` or set `serve.node_id`, otherwise serve refuses to start. A mesh with duplicate ids is worse than an explicit error.

## Modes

1. **Non-serve mode (one-shot commands)** — run a single command against a database and exit. Ideal for scripting, debugging, and shell pipelines.
2. **Serve mode (interactive REPL + networking)** — starts a server loop with an interactive prompt, optionally enabling **Net Sync** (LAN mesh) and/or **Cloud Sync** (server or client).

### Global options

| Flag | Description |
|---|---|
| `--db <path>` | Database path (default `./hako.db`) |
| `--durability <mode>` | `always` \| `interval` \| `manual` \| `on-commit` (default `on-commit`) |
| `--encryption-key <key>` | Enables storage encryption with the given master key |
| `--encrypted-cols <list>` | Comma-separated collections to encrypt (empty = all) |
| `--time` | Print execution time for the operation |
| `--count` | Print the number of results (queries and collections) |

## One-shot commands

```bash
# seed 100 documents with a few sample indexes (simple + FTS + composite)
hakocli --db ./demo.db seed users 100

# write / read / update / delete a document
hakocli --db ./demo.db set users/alice --data '{"name":"Alice","age":30,"active":true}'
hakocli --db ./demo.db get users/alice
hakocli --db ./demo.db update users/alice --data '{"age":31}'
hakocli --db ./demo.db delete users/alice

# batch write from a JSON array (path is the collection name)
hakocli --db ./demo.db set users --batch --data '[
  {"id":"a","data":{"name":"Alice","age":30}},
  {"id":"b","data":{"name":"Bob","age":25}}
]'

# query with filters, ordering, and pagination
hakocli --db ./demo.db query users --where age:gte:21 --order name:asc --limit 10 --offset 5
hakocli --db ./demo.db query users --or status:eq:active --or status:eq:pending --count

# deferred blobs: skip blob inflation, return {"__blob__": {"len","offset"}} placeholders
hakocli --db ./demo.db query bench --where active:eq:true --defer-blobs --limit 20
# resolve later with a point get (always eager):
hakocli --db ./demo.db get bench/b_121

# full-text search (match) and projections
hakocli --db ./demo.db query users --fts description:seeded
# prefix / autocomplete search (matches "seeded" from "seed")
hakocli --db ./demo.db query users --where description:matchPrefix:seed
hakocli --db ./demo.db query users --select name,age

# aggregates (count, sum, avg, min, max)
hakocli --db ./demo.db aggregate users count
hakocli --db ./demo.db aggregate users sum --field age --where active:eq:true
hakocli --db ./demo.db query users --aggregate count --aggregate avg:age
hakocli --db ./demo.db query users --aggregate min:age --aggregate max:age

# soft delete, restore, and the retention queue
hakocli --db ./demo.db delete users/alice          # soft (restoreable until swept)
hakocli --db ./demo.db delete users/alice --force  # hard (no restore)
hakocli --db ./demo.db restore-available users     # list restoreable docs
hakocli --db ./demo.db restore users/alice         # undo the delete
hakocli --db ./demo.db delete-queue                # what the next sweep will purge
hakocli --db ./demo.db sweep                       # purge expired records now

# mass update / mass delete from a query
hakocli --db ./demo.db query users --where status:eq:trial --set --data '{"tier":"pro"}'
hakocli --db ./demo.db query users --where active:eq:false --delete

# index management
hakocli --db ./demo.db index create users age
hakocli --db ./demo.db index create-composite users --fields age:asc,name:asc
hakocli --db ./demo.db index create-fts users description
hakocli --db ./demo.db index list users

# real-time watch (blocks and prints change events until Ctrl+C)
hakocli --db ./demo.db watch users

# database maintenance and inspection
hakocli --db ./demo.db collections
hakocli --db ./demo.db stats
hakocli --db ./demo.db compact

# REST-like one-shot surface: METHOD PATH [--data JSON]
hakocli --db ./demo.db rest GET users/alice
hakocli --db ./demo.db rest PATCH users/alice --data '{"age":32}'
```

Query filter syntax is `field:op:value`, where `op` is one of `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `notIn`, `match`, `matchPrefix`, `contains`, `startsWith`, `arrayContains`, `arrayContainsAny`. Array values use JSON, e.g. `tags:in:["a","b"]`. Ordering uses `field:asc` / `field:desc`. `match` runs a full-text (inverted-index) word search; `matchPrefix` is autocomplete-style prefix search over the same index (e.g. `"indom"` matches `"indomie"`).

On Windows PowerShell 5.1, inline JSON passed to `--data` loses its inner double quotes when invoking native executables. Use `--fromfile payload.json` or `cmd.exe` instead.

## Serve mode

`serve` opens the database and drops you into an interactive prompt where every CLI command keeps working (`collections`, `query users --where ...`, `peers`, `exit`).

```bash
# 1) Plain standalone server (interactive shell only)
hakocli --db ./demo.db serve

# 2) LAN Net Sync mesh node (mDNS discovery, room-key isolated)
hakocli --db ./demo.db serve --port 7070 --node-id node-1 --key my-room-key

# 3) Cloud Sync SERVER (central WebSocket hub on 0.0.0.0:8080)
hakocli --db ./cloud.db serve \
  --node-id cloud-1 --key room-key \
  --bind 0.0.0.0:8080 --token s3cret-token

# 4) Cloud Sync CLIENT (connects to the central server, offline-first)
hakocli --db ./local.db serve \
  --node-id device-1 --key room-key --room-name game \
  --server ws://cloud-host:8080 --token s3cret-token
```

The prompt shows live sync status:

```text
hako(node-1 | LAN:Online (Peers:2)) > query users --where active:eq:true --limit 10
hako(node-1 | LAN:Online (Peers:2)) > peers
hako(node-1 | LAN:Online (Peers:2)) > exit
```

Exiting the REPL (`exit` / `quit` / EOF / Ctrl+C) flushes committed writes and releases the runtime without waiting for idle sync tasks, so one Ctrl+C is enough.

| Serve flag | Purpose |
|---|---|
| `--port <u16>` | Enable **Net Sync**; start LAN mesh listener on this port |
| `--node-id <id>` | Unique node identifier |
| `--key <key>` | Room key (SHA-256 hashed for room isolation) |
| `--bind <addr>` | Enable **Cloud Sync server** on this bind address (e.g. `0.0.0.0:8080`) |
| `--server <url>` | Enable **Cloud Sync client**; connect to this server (`ws://`, `wss://`, or `https://`) |
| `--room-name <name>` | Room name for Cloud Sync clients (defaults to `default`); the server hosts any room |
| `--token <token>` | Auth token shared with the cloud server |

## Common mistakes

- **Operating a live database file.** Reads are safe; writes and especially file copies need the app stopped (or use `backup` semantics). Copy-then-inspect beats inspect-the-live-file.
- **Forgetting `--db`.** The default `./hako.db` silently creates a fresh empty database wherever you stand — the classic "where did my data go".
