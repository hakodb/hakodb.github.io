# Benchmarking HakoDB

The official harnesses live in `hakodb/hakobench` (currently `0.1.1`). Run them locally against a core checkout or a release asset. Two rules matter: **settle background work before measuring**, and **compare equal work**.

## Build (Windows, MinGW)

`HAKODB_DIR` points at a core checkout (default `../hakodb`). `-I` takes the core's release directory because `build.rs` generates `hakodb.h` next to the binaries.

```powershell
$env:HAKODB_DIR = "C:\Dev\libs\hakodb"
C:\Dev\msys64\ucrt64\bin\g++.exe -O2 -std=c++17 `
  -I$env:HAKODB_DIR\target\release benchmark.cpp `
  -L$env:HAKODB_DIR\target\release -lhakodb -o benchmark.exe
```

MinGW links directly against `hakodb.dll`; no import-lib step is needed.

## Build (Windows, MSVC)

`rustc` names the cdylib import library `hakodb.dll.lib` (not `hakodb.lib`). The repo includes `build-msvc.bat`, which assumes VS2022 Community and a core release build side by side:

```bat
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cl /O2 /std:c++17 /EHsc /I C:\Dev\libs\hakodb\target\release benchmark.cpp ^
  /link /LIBPATH:C:\Dev\libs\hakodb\target\release hakodb.dll.lib /OUT:benchmark-msvc.exe
```

At runtime `hakodb.dll` must sit next to the exe or on `PATH`. Release assets rename the import lib to `hakodb.lib`; either name links the same way.

## Build (Linux)

```sh
g++ -O2 -std=c++17 -I$HAKODB_DIR/include benchmark.cpp \
  -L$HAKODB_DIR/target/release -Wl,-rpath,'$ORIGIN' -lhakodb -o benchmark
```

`sqlite_bench.cpp` needs a local `sqlite3` development library.

## Run

```sh
./benchmark --docs=1000          # full matrix
./benchmark --docs=1000 --gate   # regression gate (Manual profile)
./benchmark --docs=10000         # larger dataset
./benchmark --profile=Always --wstats
./benchmark --index-groups=std,f2f6 --profile=Manual
./benchmark --index-groups=all --profile=Manual
./benchmark --profile=Segment --docs=1000
```

Use `--docs >= 1000` for meaningful results. Each run creates and destroys temporary `bench_data_*` directories; existing databases are not touched. A full `--docs=10000` run takes several minutes because durable profiles fsync per write and the Gaming profile moves about 500 MB.

## What it measures

| Metric | Description |
|---|---|
| `WPS (Sgl/Btc)` | Single writes/sec and batch writes/sec |
| `RPS (Seq/Par)` | Sequential and multi-threaded point-reads/sec |
| `STRESS (Get/Qry/Cmp)` | Mixed point-get, indexed-query, and composite-query throughput |
| `QPS (Off/Cur)` | Offset-pagination and cursor-pagination queries/sec |
| `Agg QPS` | Aggregate queries/sec (`sum`) |
| `Tx WPS` | Serializable transactions/sec |
| `Bulk Upd/Del` | Bulk update and bulk delete ops/sec |
| `Scan (Fwd/Rev)` | Full-table decoded scans in both directions, docs/s |
| `ScanRaw` / `ScanKey` | Byte/key-only full scans, docs/s |
| `Startup/Flush` | Engine open (ms) and clean shutdown (ms) |
| `Size` | On-disk database size |

Profiles: `Always`, `Interval`, `Manual`, `OnCommit`, `Enc_Comp` (encrypted + compressed), and `Gaming` (large documents, parallel workers). `Segment` is a diagnostic profile (0 inline budget, 1 MB rotation) that spills WAL-inlined docs into segments and reports the segment/WAL inventory plus a timed `compact()`.

The `EXTENDED` section covers additional index families. Select them with `--index-groups` (default `std`):

| Group | Indexes |
|---|---|
| `std` | Secondary indexes (`active`, `tenant`, `id`, `age`) and plain composites (`[id]`, `[tenant,score]`) |
| `f2f6` | Unique (`uniqbench.slug`), dotted (`[profile.city]`), and covering (`[tenant,active]`) indexes |
| `vector` | Vector index on `bench.emb` (32-dim), plus a kNN lane |
| `graph` | Edge index on a 200-node/200-edge graph, plus BFS and edge-write lanes |

## Settle first

A freshly written database is not a settled one. Four background stages run asynchronously: open-time index recovery, async index updates, blob persistence, and periodic maintenance (checkpoint/compaction/snapshots). Reads issued during that work measure contention, not the settled database.

```rust
// After fill, before every measured stage:
assert!(db.await_quiescent(Duration::from_secs(30)));

// Inspect what is still outstanding:
let s = db.quiescence_status();
// indexes_ready, pending_index_ops, index_backfills, pending_blob_bytes,
// queued_blob_items, maintenance_running — plus is_quiescent()
```

FFI: `hk_engine_await_quiescent(db, 30000)` and `hk_engine_quiescence_status(db)` (JSON; free with `hk_string_free`). `is_indexes_ready()` covers only the first of the four stages.

## Compare equal work

| Shape | HakoDB op | Fair comparison | Notes |
|---|---|---|---|
| Owned full scan | decoded keyset pages | `SELECT *` + owned per-row copies | Copy documents on both sides |
| Byte scan | `walk` / `hk_cursor_walk` | cursor + key movement | No decode on either side |
| Lazy (few fields) | `walk_view` + pulls | narrow `SELECT` + accessor touches | Same fields, same count |
| Point field | `viewGet` + typed getter | raw value fetch | No JSON on either side |
| JSON serve | `hk_result_set_to_json` | `json_group_array(json_object(…))` | Verify binary handling matches |
| Deep pages | keyset `start_after` at depth D | `OFFSET D LIMIT 20` | Compares seek cost with skip cost |

Use the same document count, payload shape, field count, and durability mode on both sides. Run each shape at least three times and report the median; do not compare a cold run with a warm one. State whether the numbers are cold or warm.

## Official tools

- `benchmark.cpp` — reference harness over the C ABI. Profiles across durability and workload mixes; `--gate` runs the median-of-3 regression gate on the Manual profile.
- `sqlite_bench.cpp` — SQLite mirror with the same stages, loop counts, math, and table geometry.
