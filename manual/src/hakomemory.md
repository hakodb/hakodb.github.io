# HakoMemory

HakoMemory is a local-first knowledge engine built on HakoDB. It started as a
memory layer for coding agents and is now a general-purpose store for three
kinds of data: agent memory, documents, and entity graphs. The engine, the HTTP
adapter and the agent integrations live in separate crates so you can use as
much or as little as you need.

## Library first

The public facade opens a project with an explicit configuration and an
injected embedder. It does not require a running server or environment
variables:

```rust,ignore
use hakomemory_core::embed::SharedEmbedder;
use hakomemory_core::{Engine, EngineConfig};

let embedder = std::sync::Arc::new(SharedEmbedder::mock(384));
let engine = Engine::open(EngineConfig::new("./data", embedder))?;
let project = engine.project("/absolute/project/root")?;
let hits = project.retrieve("how does hybrid search work?", 8, 60)?;
```

A project is one HakoDB directory derived from a canonical path. The same
directory, collections and indexes are available to the engine API and to every
HakoDB SDK. As with any embedded database, one process writes to a directory at
a time; use the daemon for multi-process access.

## Three modalities

| Modality | Collections | Typical use |
|---|---|---|
| Memory | `mem_episodic`, `mem_semantic`, `mem_procedural` | agent recall, lessons, session context |
| Documents | `documents`, `chunks`, `files` | notes, wikis, local RAG corpora |
| Graph | caller-defined entity/relation collections | dependencies, knowledge graphs, call graphs |

All three share the same primitives: typed documents, FTS and vector indexes,
filtered hybrid ranking, projections and local backups.

## Document ingestion

Documents are upserted by `source_uri`; a `files` manifest tracks content hash
and modification time so rescans are idempotent. Chunking strategies include
fixed line windows with overlap and header-aware splitting with parent chunks.
Each chunk keeps its source, heading path and line range, so search hits can
carry citations without a second lookup.

Source adapters are selected by extension. Filesystem text, Markdown, HTML and
JSON work in the default build; PDF and full YAML frontmatter are optional
features for deployments that need them.

## Retrieval

Search is composable:

- `vector` — nearest neighbours over embedded chunks;
- `fts` — full-text matching over chunk text;
- `hybrid` — engine-side reciprocal-rank fusion of both candidate sets;
- `hybridgraph` — hybrid seeds expanded through generic relation edges.

Filters are pushed into the engine before candidate truncation, so a small `k`
or a large corpus does not silently drop matches. A token budget is applied
after ranking, and optional parent expansion adds surrounding context to a hit.
Embedding specifications are persisted per project; changing model, provider,
dimension or metric requires an explicit re-embed instead of mixing vectors.

## Graph analytics

Traversal and analytics use the Rust engine API directly, with caller-supplied
collection, edge field, direction, depth, projection and limits. Available
operations include neighbour/path queries, subgraphs, PageRank, communities,
connected components, degree centrality, cycle detection, topological order
and graph export. Responses are normalized to entities and relations with
references resolved server-side, so clients never dereference raw reference
objects themselves.

## HTTP and clients

The server is a thin adapter over the library. It exposes project management,
memory and document CRUD, filtered search, graph analytics and maintenance
endpoints. Errors use one structured envelope with a code, message and request
id; rate-limited responses carry a retry hint. An optional JSON config file
supplies defaults, with environment variables as overrides.

An OpenCode plugin and a stdio MCP adapter are available as example clients.
They are integrations, not the centre of the project: any application can use
the library or HTTP API directly.

## Where to go next

- Engine internals: [Vector search](vector.md), [Graph traversal](graph.md),
  [Queries](queries.md).
- Desktop companion: [HakoManager (alpha)](hakomanager.md).
- Local storage guarantees: [Durability](durability.md),
  [Backup and recovery](backup-recovery.md).
