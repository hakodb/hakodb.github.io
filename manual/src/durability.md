# Durability, encryption, compression

All three are `HakoConfig` fields, set before `open` (encryption key cannot be added to an existing database afterwards — the choice is baked into the files).

```rust,ignore
use hakodb::config::{DurabilityMode, HakoConfig};

let mut cfg = HakoConfig::default();
cfg.durability_mode = DurabilityMode::OnCommit;  // see below
cfg.encryption_key = Some("32+ character secret here".into());
cfg.encrypted_cols = None;                       // None = encrypt everything
db.flush()?;   // force everything to disk now, regardless of mode
```

## Durability modes

| Mode | Crash safety | Cost |
|---|---|---|
| `Always` | Every write fsync'd | Slowest, safest. Default. |
| `Interval` | fsync on a timer | Bounded loss window, much faster. |
| `OnCommit` | Batch commit is atomic | Grouped writes, single flush. |
| `Manual` | Only on `flush()` | Fastest, you own the risk. |

Development and bulk import usually want `Manual` + explicit `flush()`; production usually wants `Always` or `Interval`. Benchmarks in this repo's history were measured per-mode — compare numbers only within the same mode.

## Encryption

ChaCha20-Poly1305 over WAL and segment payloads. `encrypted_cols = None` encrypts all collections; `Some(set)` encrypts only those. Key management is yours: lose the key and the data is unrecoverable, by design.

Critical interaction: at-rest encryption and sync are **independent** — encrypted collections replicate as plaintext unless the sync guards refuse (see the encryption posture in the README). Same key on every node that must share a room.

## Compression

The `compression` cargo feature (default-on) enables zstd for values over ~2KB when it actually shrinks them. Builds without the feature store raw and **fail closed** when opening zstd payloads. `compression_level` tunes the tradeoff; the blob threshold (`value_blob_threshold_bytes`) decides what leaves the hot path.

## Common mistakes

- **Encrypting after writing plaintext.** The key applies from file creation. To encrypt an existing database: open a new encrypted database and copy collections over.
- **Short or shared-across-environments keys.** One key per environment; production keys never appear in code or logs.
- **Manual durability in production without a flush strategy.** If you pick `Manual`, every write path must end in a periodic `flush()` — no exceptions, no "I'll add it later".
