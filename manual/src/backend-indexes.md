# Backend indexes

```sh
curl -X POST localhost:3000/api/indexes \
  -H 'Content-Type: application/json' \
  -d '{"collection":"posts","fields":["age"],"kind":"simple"}'
curl 'localhost:3000/api/indexes?collection=posts'
```

Kinds: `simple` (default, exactly 1 field), `composite` (>1 field — equality fields first, sort field last, so filter+order walks once), `fts` (1 field). Vector/graph/traverse go through their own endpoints (`/api/vector-index`, `/api/vector-search/{collection}`, `/api/traverse-index`, `/api/traverse-search/{collection}`, `/api/edge-index`) — the generic endpoint rejects them clearly instead of guessing.

**Nothing is automatic.** `auto_provision` creates collections plus only the `[[indexes]]` you declare; no index is inferred from queries. A filtered or ordered query without a matching index is a full scan and full decode. Declare an index for every field you filter or sort by.

Per-driver honesty: `unique` and `drop_index` work where the driver supports them, else a clear 400. Non-hako drivers serve vector/graph by gateway exact scan (capped) or reject create+search with 400 — never silent unbounded scans.

Archive moves and lazy residency are hako-only: `POST /api/relocate {src, dst, ids[]}` (idempotent, timestamp-preserving), `/api/collections/load|unload`, `GET /api/collections/unloaded`. Other drivers answer 400.

## Common mistakes

- **Ordering without an index.** An order-only query without an index scans and sorts the collection. Index the sort field.
- **Creating the vector index after writing.** Pre-index vectors land as plain arrays and stay unindexed on hako. Index first, write second.
