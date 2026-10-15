# CLI (hakocli)

`hakodb/hakocli` (currently `0.2.8`): command-line manager, REPL, and serve mode for any HakoDB database. The fastest way to inspect, seed, and operate a database file without writing code.

```sh
hakocli --db ./data set users/1 --data '{"name":"alice"}'
hakocli --db ./data get users/1
hakocli --db ./data query users --where 'age:gte:18' --limit 50
hakocli --db ./data traverse create docs
hakocli --db ./data traverse paths docs a --direction outgoing --via rel --weight w
hakocli --db ./data serve --port 8080        # REPL + serve mode
```

Command groups: `get/set/update/delete`, `query` (+ `aggregate`), `traverse` (`create`, `create-edge`, `paths`), `vector` (`create`, `search`), `index`, `watch`, `tx*`, `backup/compact/vacuum/relocate/load/unload`, `stats`, `peers` (serve mode), `collection-local`.

Global flags: `--db` (default `./hako.db`), `--durability`, `--encryption-key` / `--encrypted-cols`, `--time`, `--count`, `--config` (TOML; flags win over file).

Use it for: seeding dev data, inspecting production files offline (stop the app first, or copy the directory), running one-off traversals/vectors, and smoke-testing sync rooms with two CLIs on one LAN (`serve` + `peers`).

## Common mistakes

- **Operating a live database file.** Reads are safe; writes and especially file copies need the app stopped (or use `backup` semantics). Copy-then-inspect beats inspect-the-live-file.
- **Forgetting `--db`.** The default `./hako.db` silently creates a fresh empty database wherever you stand — the classic "where did my data go".
