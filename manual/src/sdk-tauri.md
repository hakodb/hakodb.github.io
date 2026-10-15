# Tauri SDK (Rust gateway + TypeScript client)

Two halves: `hakotauri` (`0.4.10`, Rust gateway crate) exposes the engine as binary Tauri commands; `@hakodb/tauri` (`0.3.5`, `hakodb/hakotaurits`) calls them over `invoke` with MessagePack payloads and `onSnapshot` listeners.

```rust,ignore
// src-tauri: register the gateway (see hakotauri README for the full setup)
tauri::Builder::default()
    .invoke_handler(/* hako commands */)
    .run(tauri::generate_context!())
```

```ts
import { collection, doc, setDoc, getDoc, query, where, getDocs, onSnapshot } from "@hakodb/tauri";

await setDoc(doc(db, "users", "1"), { name: "alice" });
const snap = await getDoc(doc(db, "users", "1"));
const rows = await getDocs(query(collection(db, "users"), where("age", ">=", 18)));
const unsub = onSnapshot(collection(db, "users"), (docs) => render(docs));
```

Notes:

- The gateway re-exports engine types (`Hako`, `HakoConfig`, `HakoDoc`, `Value`, `Query`, …), so Tauri backend code uses the same API as the [Rust core](crud.md) without a direct `hakodb` dependency.
- Sync planes are opt-in features on the gateway (`net-sync`, `cloud-sync`, `socket-sync`): enable what the app needs; the TS side calls the same sync ops.
- `flushDatabase` / `listStorageKeys` cover the consumer ops (durability control, storage inspection).
- Graph and vector ops are wired through (`createTraverseIndex`, `findPaths`, `createEdgeIndex`, `findNear`).

## Common mistakes

- **Calling sync ops without enabling the feature.** The gateway compiles per-feature; a sync call against a gateway built without it fails at invoke time. Match features to calls.
- **Forgetting the gateway is per-window for listeners.** Window-scoped subscriptions die with the window — resubscribe on navigation, and clean up (`unsubscribe`) like any listener.
