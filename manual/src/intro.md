# Introduction

HakoDB is an embedded document database: a library you link into your process, not a server you operate. It stores typed JSON-like documents, queries them with filters/ordering/cursors, and optionally replicates them over LAN or a cloud hub.

> Tested against `hakodb 0.15.3`. API shown is the Rust engine; other languages reach the same engine through the [C ABI](../#c-abi) and per-language SDKs.

## Five-minute quickstart

```toml
[dependencies]
hakodb = "0.15"
```

```rust
use hakodb::config::HakoConfig;
use hakodb::document::hako_doc::HakoDoc;
use hakodb::document::value::Value;
use hakodb::engine::Hako;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db = Hako::open("./data", HakoConfig::default())?;

    let mut doc = HakoDoc::default();
    doc.insert("name", Value::String("alice".into()));
    doc.insert("age", Value::Int(30));
    db.put("users", "1", &doc)?;
    db.flush()?;

    let got = db.get("users", "1")?.expect("just wrote it");
    println!("{:?}", got.get("name"));
    Ok(())
}
```

That is the whole deployment model: `open` a directory, read and write. No daemon, no connection string, no migrations to run.

## Where to go next

- New to embedded databases? Read [Concepts](concepts.md), then [Choosing a mode](choosing-mode.md).
- Want a feature tour? [CRUD](crud.md) → [Queries](queries.md) → [Indexes](indexes.md).
- Need similarity or graph queries? [Vector search](vector.md), [Graph traversal](graph.md).
- Shipping to production? [Durability](durability.md), [Backup and recovery](backup-recovery.md), [Errors](errors.md).
