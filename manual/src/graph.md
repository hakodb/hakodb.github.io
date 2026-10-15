# Graph traversal

Documents link with `Reference` values (`{"__ref__": "collection/id"}` in JSON). Traversal follows them without joins.

```rust,ignore
use hakodb::index::traverse::{TraverseDir, TraverseSpec};

// 1. Track edges (opt-in per collection)
db.create_traverse_index("docs")?;

// 2. Walk: out, in, or both — BFS, depth-capped, deterministic order
let spec = TraverseSpec {
    direction: TraverseDir::Outgoing,
    edge_field: None,   // None = follow any reference field
    max_depth: 10,      // 1..=32, hard errors outside
    limit: 100,
    via_edge: None,
    weight_field: None,
};
let hits = db.find_paths("docs", "a", &spec)?;   // Vec<TraverseHit>
```

Each hit carries its depth from the start node. Depth is hard-capped at 32; visited sets keep cyclic graphs terminating.

## Weighted shortest paths

For costed graphs, store edges as documents with `_from`/`_to` references (plus any numeric weight field) and register the collection:

```rust,ignore
db.create_edge_index("rel")?;
let spec = TraverseSpec {
    direction: TraverseDir::Outgoing,
    edge_field: None,
    max_depth: 10,
    limit: 100,
    via_edge: Some("rel".into()),
    weight_field: Some("w".into()),
};
let hits = db.find_paths("nodes", "a", &spec)?;  // cost-ordered, hits carry `cost`
```

Missing or non-numeric weights count 1.0; negatives clamp to 0. Without `via_edge`, the same call runs unweighted BFS.

## The fail-loud rule

Incoming walks need reverse state: a tracked anchor (backlinks) or a registered edge collection. If neither exists, the query **errors** instead of returning an empty list. An empty result therefore always means "no path", never "forgot the index". If you see the error, create the missing index first.

As with vectors, traversal indexes rebuild locally on every node — sync carries definitions, not state.

## Common mistakes

- **Writing edges before `create_traverse_index`.** Backlink tracking starts at creation; pre-existing references are untracked for incoming walks (re-write them after creating the index).
- **Treating references as joins.** There is no multi-collection join planner; traversal is explicit walks from a start node.
