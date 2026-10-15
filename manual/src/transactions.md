# Batches and transactions

Two levels, pick by what can go wrong:

```rust
use hakodb::engine::BatchMutation;

// Level 1: atomic batch — all mutations commit together, no isolation checks
db.write_batch(vec![
    BatchMutation::Put { collection: "users".into(), doc_id: "1".into(), doc },
    BatchMutation::Delete { collection: "users".into(), doc_id: "2".into() },
])?;

// Level 2: serializable transaction — staged reads + writes, commit fails
// if anything you read changed underneath you
let mut tx = db.begin_serializable_transaction();
let balance = tx.get(&db, "accounts", "alice")?;  // recorded read
tx.put("accounts", "alice", new_doc);             // staged (owned doc)
let ids = tx.commit(&db)?;                        // Err on conflict: retry
```

- Use **batches** for bulk loads and multi-doc writes that must land together.
- Use **serializable transactions** for read-modify-write cycles (balances, counters, reservations). A conflict error is normal operation — retry the whole function, don't patch around it.

## Common mistakes

- **Retrying only the commit.** Re-run the full read-compute-write function; reusing stale reads guarantees another conflict.
- **Transactions across sync boundaries.** A transaction is local to one process. Two nodes editing the same document converge by last-write-wins, not by transactions — design for that.
