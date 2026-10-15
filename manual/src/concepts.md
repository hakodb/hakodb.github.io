# Concepts

## Documents and collections

A **collection** is a named set of documents (like a table that never needed a schema). A **document** is a map of field names to typed values. Every document has an id — a string you choose (`"1"`, `"user-42"`).

Values are typed: `Null`, `Bool`, `Int(i64)`, `Float(f64)`, `String`, `Binary(bytes)`, `Timestamp`, `Array`, nested documents, and `Reference { collection, doc_id }` (a pointer used by [graph traversal](graph.md), not a join).

## In-process model

Your app *is* the database host. `Hako::open("./data", cfg)` memory-maps storage files and spawns background workers (indexing, compaction, WAL flusher) inside your process. There is no server process and no network port unless you enable sync.

On disk, `./data` holds segment files, the WAL, and index snapshots. Copying that directory while the database is [flushed and quiet](backup-recovery.md) is a valid backup.

## Reads and writes

- Writes go through an in-memory batch, then the WAL, then segments. `flush()` forces everything to disk now; durability modes decide what happens if you don't call it (see [Durability](durability.md)).
- Reads are positional and lock-free against concurrent readers: many threads can `get`/`query` while one writer commits.

## Common mistakes

- **Treating collections like tables with fixed columns.** There is no schema and no migration step; different documents in one collection may have different fields. The query planner uses indexes when they exist and sweeps when they don't — both are correct, just different speeds.
- **Using the document id as a field.** The id is the key, not a field. If you also store it inside the document, the two can drift.
- **Storing huge blobs inline.** Payloads above the blob threshold are offloaded automatically, but fetching them still costs I/O. Keep hot documents small; put large bytes behind blob fields and resolve them only when needed (`resolve_document_blobs`).
