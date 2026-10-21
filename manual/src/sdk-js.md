# JavaScript / TypeScript SDK

Package `@hakodb/client` (`hakodb/hakojs`, currently `0.5.22`). Two layers: a high-level Firestore-shaped client (`client.ts`) over native FFI bindings (`native.ts`; `koffi` on Node, Bun FFI on Bun).

```sh
npm i @hakodb/client
```

`native.ts` loads the HakoDB cdylib. Resolution order: `loadNativeBindings(explicitPath)` → `HAKODB_LIB_PATH` env → `./native/<lib>`. Populate it with the repo's sync script:

```powershell
.\sync-native.ps1 -CoreDir C:\Dev\libs\hakodb
.\sync-native.ps1 -Tag v0.16.7
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
- References use `{__ref__: "collection/id"}`; graph and vector ops (`createTraverseIndex`, `findPaths`, `createEdgeIndex`, `shortestPaths`, `createVectorIndex`, `findNear`) are on the client.

## Common mistakes

- **Forgetting the native library on a new machine.** The npm package ships the Windows DLL; other platforms need `libraryPath` pointed at a local release asset until per-platform bundles land.
- **Treating `onSnapshot` as a query.** It subscribes; the first callback is the current state, later ones are deltas. Unsubscribe when the view unmounts.
