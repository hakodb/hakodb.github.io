# Reading data: choosing the right path

HakoDB offers four read granularities for the same stored bytes. Rule of thumb: **return the least materialization that answers the question.**

| Path | Per-row work | Use when |
|---|---|---|
| `get` / `query` (decoded) | Full owned `HakoDoc` | You need whole documents as values |
| `query_raw` | Pinned bytes, no decode | Export, hash, relay, count bytes |
| `walk` | Borrowed bytes, no allocations | Full scans: count, filter, copy out |
| `get_view` / `walk_view` | Borrow and pull only touched fields | Sparse reads: a few fields out of many |

All four return the same field values for the same stored document. See [Benchmarking](benchmarking.md) for measuring a read path on your hardware.

## Point reads

```rust
// Whole document, owned. Hot repeats skip decode via an internal cache.
let doc: Option<HakoDoc> = db.get("orders", "id-123")?;

// Borrowed view: no decode, no interning, no cache churn. Pull fields lazily.
if let Some(view) = db.get_view("orders", "id-123")? {
    if let Some(Value::Int(total)) = view.get("total") { /* ... */ }
    let full: HakoDoc = view.to_owned_doc().expect("valid");
}
```

Views never inflate blobs: a blob-backed field reads back as its link
placeholder. Resolve through a full decode when you need the bytes
(`to_owned_doc` + `resolve_document_blobs`, or plain `get`).

FFI mirrors both: `hk_engine_get` / `hk_doc_to_json` for owned docs,
`hk_view_get` + typed `hk_view_get_int/float/bool/str/bytes` for lazy
pulls, `hk_view_to_doc` as the escape hatch. SDKs expose the same
shapes (point views with lazy numeric/bool pulls, no decode).

## Scans

```rust
// Decoded, paged. Order/pagination handled by the planner.
let mut q = Query::new("orders").order_by("id", true);
q.limit = Some(1000);
// ... anchor with start_after(last_id) per page ...

// Raw bytes, paged. Same paging, no decode.
let rows: Vec<(String, Arc<Vec<u8>>)> = db.query_raw(q)?;

// Zero-alloc walk. One call, borrowed rows, false stops early.
let n = db.walk(q, &mut |id: &str, bytes: &[u8]| { /* ... */ true })?;

// Lazy walk. Same shape, each row lent as a DocView.
let n = db.walk_view(q, &mut |id: &str, view: &DocView| { /* ... */ true })?;
```

Raw and walk require index-satisfied filters and ordering (they cannot
match or sort without decoding) and return errors otherwise — loud, not
silent. Bytes are **opaque storage encoding**: hash/count/export them,
decode with `HakoDoc::decode`, never persist or compare across
versions. FFI: `hk_query_execute_raw` + result-set fns,
`hk_cursor_walk` / `hk_cursor_walk_view` with C callbacks.

## Pagination

Prefer keyset paging. `offset` exists, but it is a skip scan: the rows are
still produced and discarded. Order by `id`, take a page, bind the last row
as the next anchor (`start_after`); descending is symmetric (same fast path
both directions, ~1.1x apart):

```rust
let mut q = Query::new("bench").order_by("id", false);
q.limit = Some(1000);
// per page: q = q.start_after(vec![Value::String(last_id)]);
```

`limit`/`offset` truncate downstream; keyset pages seek directly to the
anchor. Offset-based paging still walks every skipped row, so its cost
grows with depth.

## Before you measure or paginate: readiness

`Hako::open` returns while index recovery still runs in the
background. Queries issued first can plan full scans, so cursor bounds
may be ignored and pages may repeat. Pending writes gate only their own
collection; open-time recovery gates all of them. Poll before scanning:

```rust
while !db.is_indexes_ready() { /* sleep briefly, bounded */ }
// Measuring? Settle everything instead:
db.await_quiescent(Duration::from_secs(30)); // indexes + index worker + blobs + maintenance
```

`await_quiescent` waits for indexes, the index worker, blobs, and
maintenance. `quiescence_status()` reports what is still outstanding.
FFI: `hk_engine_await_quiescent` / `hk_engine_quiescence_status`. Settle
before scans when the result needs to reflect a stable database.

## Blob semantics (the fine print)

Values over `value_blob_threshold_bytes` (16KB default) live in the blob
file; documents carry `BlobLink` placeholders. Reads inflate transparently
except on raw/view paths (by design — resolve explicitly). One asymmetry
to know: blob storage is type-erased bytes, so inflation restores
`String` for valid UTF-8 and `Binary` otherwise. Text round-trips exactly;
binary that happens to be valid UTF-8 comes back as text. Changing that
needs per-blob type tags — a separate, deliberate decision.
