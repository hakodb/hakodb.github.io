# Vector search

```rust,ignore
use hakodb::index::vector::Metric;

db.create_vector_index("articles", "embedding", 384, Metric::Cosine)?;
let hits: Vec<(String, HakoDoc)> = db.find_near("articles", "embedding", &query_vec, 10)?;

db.drop_vector_index("articles", "embedding")?; // definition + graph
```

Vectors are stored as binary little-endian `f32` arrays in a regular field. Search walks an HNSW graph and rescores exactly — nearest first.

Rules:

- **Index before write.** Vectors written before the index exists are not searchable until re-indexed; create the index first.
- **One model everywhere.** Query and corpus must share the embedding model (same dimensions and geometry). A dimension mismatch is a hard error, never silent truncation.
- **The index does not embed.** Turning text or images into vectors is your pipeline (a small ONNX sidecar or a vendor embedding API). Without it, the index sits empty.
- **Readiness applies.** `vector_index_complete(collection, field)` tells you the graph caught up; early queries fall back gracefully.

## Common mistakes

- **Mixing models or dimensions** across corpus and query — the single most common vector bug, in any database.
- **Expecting the graph to sync.** Index definitions replicate; HNSW graphs rebuild locally on each node from replicated documents.
