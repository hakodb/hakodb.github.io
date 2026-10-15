# Errors and fail-closed rules

Every fallible call returns `Result<_, HakoError>`. The variants:

| Variant | Meaning | Typical cause |
|---|---|---|
| `Io` | OS/filesystem failure | Disk full, permissions, missing directory. |
| `LockPoisoned` | Internal lock poisoned | A prior panic while holding it — restart the process. |
| `StorageError` | WAL/segment/blob failure | Torn files, zstd decode failure, blob resolve miss. |
| `QueryError` | Query rejected before running | Unsatisfied filters/ordering, unsupported scan shape. |
| `IndexError` | Index operation failed | Building on a missing collection, bad definition. |
| `Corrupt` | Fail-closed refusal | Denied access, out-of-range traverse depth, compressed payload on a compression-less build. |
| `InvalidInput` | Bad argument | Empty ids, zero depth/limit, malformed reference. |

Design rules behind them (these never change silently):

1. **Loud over empty.** A missing index, untracked anchor, or denied collection errors — it never returns a plausible-looking empty result. An empty result always means "no data".
2. **Ranges are hard errors.** Traverse depth outside 1..=32, zero limits, empty ids: rejected, never clamped.
3. **Capability mismatches fail at the boundary.** zstd payload on a no-compression build, encrypted room with a keyless peer, old peer in a new protocol: refused with a named error, at open/handshake time where possible.
4. **Panics don't cross FFI.** The C boundary catches panics per call and reports them through `hk_last_error` — the process survives a bad call.

## Handling pattern

```rust
match db.get("users", id)? {
    Some(doc) => render(doc),
    None => render_missing(),   // missing is data, not failure
}
```

Match on `None` for absence; match on `Err` for failure. Logging the full `HakoError::Corrupt` message on failure is encouraged — the messages name the collection, index, or rule involved.

## Common mistakes

- **Treating `Ok(None)` as an error.** It means "no such document". Retrying won't create it.
- **Swallowing `Corrupt` with a default.** Fail-closed errors are guardrails; defaulting past them reintroduces the exact silent wrongness they prevent. Fix the cause (create the index, distribute the key, fix the range).
