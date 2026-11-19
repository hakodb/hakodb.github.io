# HakoManager (alpha)

HakoManager is a desktop manager for local HakoDB data directories. It is a
graphical companion to the engine — you do not need it to use HakoDB — and it
is currently **alpha**: the file format is the engine's own format, but the UI
and release packaging are still evolving.

The application is a thin shell over a UI-independent Rust core: a Tauri 2
window hosts a React frontend, and every action goes through one command gate
into the shared core. That means the same dispatch logic used by tests can be
reused by other clients later.

## What it does

- **Workspace**: open one or more local database directories, keep the active
  profile/collection between launches, and reopen sessions automatically.
  Encryption keys are entered per session and are never persisted.
- **Explorer**: browse databases and collections, inspect profile/collection
  metadata, and switch between the Database and Inspector panels.
- **Documents**: table, standard and raw-JSON views with resizable columns and
  horizontal scrolling; filter by any field present in the loaded rows; export
  the current list; click a row to open it in the document editor.
- **Query console**: a text box for fluent queries and manager commands, with
  completion, history and visible results. Filters, ordering, limits,
  projections and aggregates are all expressed in one line.
- **Operations**: backups, compaction and vacuum are available from the shell;
  destructive operations snapshot the database first.
- **Updates**: release builds ship installers and flat binaries, and the app
  checks signed update manifests. Installing an update always requires user
  confirmation.

## Data model

HakoManager does not introduce a new database format. A "database" is simply a
HakoDB directory with collections of typed documents. The manager writes
standard engine documents, so the same data is readable from the core library,
the CLI, or any SDK that opens the same directory.

Keep one writable process per directory. If several applications need the same
data, run a service that owns the directory and let clients talk to it rather
than opening two writers.

## Safety notes

- Take a backup before upgrades or bulk operations; the built-in destructive
  commands create sibling backup snapshots automatically.
- Read-only mode exists for inspecting a database that is already held by
  another process.
- Encrypted databases need their key again after every restart; the key lives
  only in memory.

## Where to go next

- Engine concepts: [Concepts](concepts.md), [CRUD](crud.md), [Queries](queries.md).
- Local storage guarantees: [Durability](durability.md), [Backup and recovery](backup-recovery.md).
- A related tool for knowledge/RAG workloads: [HakoMemory](hakomemory.md).
