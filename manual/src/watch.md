# Watch streams

```rust,ignore
let rx = db.watch_collection("users");
while let Ok(event) = rx.recv() {
    println!("{:?} {}", event.kind, event.path);   // Put/Delete + "collection/id"
}
```

`watch_collection` returns a channel receiver of `ChangeEvent` (`Put` / `Delete`, with the affected `collection/id` path). Events fire for local writes and for applied sync writes — one stream covers both.

Rules:

- The receiver is blocking (`recv`) — dedicate a thread or use `try_recv` in a loop.
- Streams are per collection, in-process. Across processes/languages, use the FFI watch bridge or sync + watch on each node.
- A slow consumer can lag: treat the stream as notifications ("re-read this id"), not as a data pipe.

## Common mistakes

- **Doing engine writes inside the callback thread that also holds a read.** Keep handlers short: copy the id, process elsewhere. (Same rule as zero-copy walks: never re-enter the engine from inside a borrowed context.)
- **Assuming at-least-once delivery across restarts.** The stream is live-only; on restart, diff current state yourself (compare versions, then subscribe).
