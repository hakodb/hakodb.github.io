# JavaScript / TypeScript SDK

Package `@hakodb/client` (`hakodb/hakojs`). Two layers: a high-level Firestore-shaped client (`client.ts`) over native FFI bindings (`native.ts`; `koffi` on Node, Bun FFI on Bun).

```sh
npm i @hakodb/client
```

`native.ts` loads the HakoDB cdylib. Resolution order: `loadNativeBindings(explicitPath)` → `HAKODB_LIB_PATH` env → `./native/<lib>`. Populate it with the repo's sync script:

```powershell
# from a local core checkout (build it first: cargo build --release --features header)
.\sync-native.ps1 -CoreDir <core-checkout>
# or from a core release (pass the tag you want)
.\sync-native.ps1 -Tag <core-release-tag>
```

Binaries under `native/` are git-ignored.

```ts
import { HakoClient } from "@hakodb/client";

const db = await HakoClient.open("./data");
await db.set("users", "1", { name: "alice", age: 30 });
const snap = await db.get("users", "1");
console.log(snap.data());

const rows = await db.collection("users")
  .where("age", ">=", 18)
  .orderBy("age", "desc")
  .limit(50)
  .get();

const unsub = db.collection("users").onSnapshot((docs) => render(docs));
```

Notes:

- `open(path, options?)` loads `native/hakodb.dll` (shipped) or `options.libraryPath` / `HAKODB_LIB_PATH`. A failed open throws with `native.lastError()`.
- Queries mirror Firestore spelling (`where`, `orderBy`, `limit`, `onSnapshot`) with HakoDB operators (`== != > >= < <= match matchPrefix contains startsWith in not-in array-contains array-contains-any`).
- `HakoConfig` exposes durability/encryption/workers; `NetSyncer` and `CloudSync` classes wrap the sync planes; `Transaction` and `WriteBatch` mirror the engine.
- References use `{__ref__: "collection/id"}`. Graph and vector ops are on the collection; `findNear()` / `hybridSearch()` accept an optional `filters` array and use the canonical filtered lanes, while `findPathsFull()` / `shortestPathsFull()` are the canonical graph lanes. Edge indexes and tuned vector V2 parameters remain advanced APIs.
- Canonical pairs: `effectiveConfig()` for introspection, `ensureIndexes()` / `dropIndexes()` for schema. `quiescenceStatus()`, `isIndexesReady()`, `getStats()`, granular `create*`/`drop*` index calls, `findPaths()`, `shortestPaths()`, and `Query.getJson()` are advisory-deprecated — they still work and emit a one-time warning.
- Read lanes are not interchangeable. `get()` returns full `HakoDocData[]` and pays `JSON.parse`; `get({ mode: "json" })` is pinned-byte egress without JS objects; `select(...).get()` returns projected rows; `getViewRows(fields)` returns typed borrowed views with only the requested fields; `getRaw()` / `viewDoc()` are engine-only diagnostics whose checksums are count-only or partial. Use the document lane for application code and label diagnostic lanes explicitly in benchmarks.
- Deletes are soft by default; `deleteEx(ref, force)` opts into a hard delete, and `restore` / `restoreAvailable` / `deleteQueue` / `sweepNow` wrap the retention surface on the client.

## Common mistakes

- **Forgetting the native library on a new machine.** The npm package ships the Windows DLL; other platforms need `libraryPath` pointed at a local release asset until per-platform bundles land.
- **Treating `onSnapshot` as a query.** It subscribes; the first callback is the current state, later ones are deltas. Unsubscribe when the view unmounts.
