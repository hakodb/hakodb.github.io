# Agent engine (hakoagent)

`hakoagent` is an agent memory, skill, and code-graph engine on top of the HakoDB embedded
database (`hakodb` crate via the C ABI). It gives coding agents — OpenCode, Claude Code, or
a custom harness — persistent project context across sessions while minimizing LLM token
use: every recall, cache hit, and graph query is answered locally, not by a model call.

- Repository: https://github.com/hakodb/hakoagent
- Platforms: Windows x86_64 and Linux x86_64 (macOS: not yet — the native library has
  no released macOS build; hakoagent requires the real engine and has no fallback).

## Install

```sh
git clone https://github.com/hakodb/hakoagent.git
cd hakoagent
python install.py              # project-local install (./hakoagent* + AGENTS.md + .opencode/ + lib/)
python install.py --global     # global: ~/.local/bin (Linux), %LOCALAPPDATA%\hakoagent\bin (Windows)
```

The installer is a Python stdlib script. It downloads the native hakodb library from the
latest [hakodb release](https://github.com/hakodb/hakodb/releases) (`.dll` on Windows,
`.so` on Linux, glibc variants tried oldest first), verifies it against the release
`SHA256SUMS`, and proves it loads via `ctypes` before finishing.

`install.py` never overwrites a pre-existing `AGENTS.md` in the target project; it skips
with a message and points at the source template (`assets/AGENTS.md`) for manual merging.

## Core concepts

Everything is stored in the project's `.hakoagent/` directory as hakodb collections:

| Collection | Purpose |
|------------|---------|
| `sessions` | Agent session records |
| `events` | Append-only log of every action |
| `decisions` | Architecture decisions with rationale and consequences |
| `findings` | Codebase findings, bugs, patterns, error notes |
| `code_index` | Symbols, files, dependencies (graph traversal) |
| `tasks` | Tasks with target, priority, definition of done, status |
| `context_cache` | TTL'd compact summaries reducing LLM calls |
| `skills` | Successful patterns extracted from completed tasks |
| `lessons_learned` | Failure lessons to avoid repeating |

`hakoagent` itself is a single stdlib-only Python file. `hakoagent-cli` and `hakoagent-mcp`
are thin launchers; one implementation serves both, selected by the executable name or the
`HAKOAGENT_MODE` environment variable.

## CLI

One-shot commands (see `hakoagent help` for the full list):

```sh
hakoagent init --db ./.hakoagent/hakoagent.db --collections all   # once per project
hakoagent index                       # scan + index the codebase into the graph
hakoagent recall "Rust error handling" --limit 5   # vector + FTS retrieval
hakoagent impact src/main.rs          # blast radius before editing
hakoagent cache put "<query>" "<summary>" [ttl]   # store an expensive answer
hakoagent cache get "<query>"         # reuse it locally, zero LLM calls
hakoagent graph traverse <node> in|out <depth>     # dependency traversal
hakoagent graph shortest-path <from> <to>          # Dijkstra over the graph
hakoagent task create "<title>" "<target>" "<dod>" [priority]
hakoagent skill list                  # skills extracted from completed tasks
hakoagent events --limit 20           # append-only action history
hakoagent vigilance                   # forgotten files, TODO leftovers, regressions
```

`task complete` quietly re-indexes when the working tree has changes, and completed tasks
auto-extract into deduplicated skills.

## MCP server

MCP is off by default. Per project:

```sh
hakoagent mcp enable    # writes .hakoagent/mcp-enabled + mcp.servers.hakoagent in opencode.json
hakoagent mcp status
hakoagent mcp disable
```

The server speaks JSON-RPC over stdin/stdout. Tools include `save_doc`, `load_doc`,
`recall`, `cache_put`/`cache_get`/`cache_stats`, `events`, `revision.list`, `skill.*`,
`task.*`, `sync.*`, `graph.*` (traverse, shortest_path, impact, search, query, adr, ...),
`vigilance`, `bug_scan`, and `team.*`. The agent-connection examples live in
`assets/AGENTS.md` inside the repository (installed as `AGENTS.md` into your project).

## Token economy

HakoAgent's contract with agents is: spend tokens on context, not on re-reading the world.
The engine side:

- `recall` answers from the local index and cache first — a hit is a zero-LLM answer.
- `context_cache` stores distilled answers with TTL; repeat questions are local.
- The code graph lets an agent ask "what depends on X" instead of re-scanning source.
- Skills carry distilled, deduplicated operational knowledge; `--summary` keeps context lean.

The behavioral side lives in the installed `AGENTS.md` (recall before searching, batch
reads, one targeted check while iterating, full suite once at the end) — adapted from the
org-wide efficiency standard.

## Uninstall

```sh
python install.py --uninstall           # scope-matched: project-local or global
python install.py --uninstall --remove-data   # also deletes .hakoagent/
```

Uninstall removes the binaries, downloaded native library, skills/commands, and any
`AGENTS.md` that was installed by hakoagent — pre-existing user `AGENTS.md` files are kept.
