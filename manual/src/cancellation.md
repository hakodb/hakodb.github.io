# Cancellation

Long maintenance and bulk operations accept a `CancelToken`. Cancellation is
cooperative: you ask the operation to stop, and it stops at its next safe
checkpoint. It never leaves a half-written document or a half-swapped segment.

## Token

`CancelToken` is a cheap-to-clone flag. Clone it into the thread that should be
able to stop the work, and pass the original to the operation.

```rust,ignore
use hakodb::cancel::CancelToken;

let token = CancelToken::new();
let signal = token.clone();

std::thread::spawn(move || {
    // Your own timeout, client disconnect, or shutdown signal.
    signal.cancel();
});

db.delete_where_with_cancel(Query::new("events").where_eq("stale", Value::Bool(true)), &token)?;
```

`cancel()` is idempotent and safe from any thread. `is_cancelled()` observes the
flag; `check()` returns `Err(HakoError::Cancelled)` once it is set.

## Operations

| Method | Cancellation point | What survives |
|---|---|---|
| `delete_where_with_cancel` | During the matching scan and before the delete batch. | Cancelling before the batch writes nothing. The batch itself is atomic. |
| `patch_where_with_cancel` | During the matching scan and before the patch batch. | Cancelling before the batch writes nothing. The batch itself is atomic. |
| `compact_with_cancel` | Before each shard, during entry collection, and before the atomic swap. | Shards already merged stay merged. A cancelled target segment is removed; original segments stay intact. Retry safely. |
| `vacuum_with_cancel` | During the blob scan and before the `blobs.tmp` rename. | The temp file is removed; `blobs.dat` and every document stay as they were. |

The plain `delete_where`, `patch_where`, `compact`, and `vacuum` methods behave
exactly as before and never cancel.

## Errors

A cancelled operation returns `HakoError::Cancelled`, classified as
`ErrorKind::Cancelled` (stable code `5` in the C ABI error-kind surface).
It is not retryable with the same token: the token stays cancelled. Start a new
operation with a fresh token if the work is still wanted.

Bulk operations check cancellation before their single write batch, so there is
no partially deleted or patched match set. If cancellation arrives after that
batch commits, the call returns success; the work is already durable.

## Scope

Cancellation currently covers the Rust API. The C ABI does not expose a token
handle yet, so C-based SDKs keep the non-cancellable methods.
