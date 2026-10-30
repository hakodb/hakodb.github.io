# Tauri SDK (Rust gateway + TypeScript client)

Two halves: `hakotauri` (Rust gateway crate) exposes the engine as binary Tauri commands; `@hakodb/tauri` (`hakodb/hakotaurits`) calls them over `invoke` with MessagePack payloads and `onSnapshot` listeners. The gateway and client move together: the TypeScript op enum must match the Rust `HakoOp` enum.

```sh
npm i @hakodb/tauri
```

Register the gateway in `src-tauri`:

```rust,ignore
tauri::Builder::default()
    .manage(hakotauri::HakoGateway::new(db))
    .manage(hakotauri::net_sync::NetSyncState::new(app_handle.clone()))
    .manage(hakotauri::cloud_sync::CloudSyncState::new(app_handle.clone()))
    .invoke_handler(tauri::generate_handler![
        hakotauri::gateway::hako_exec,
        hakotauri::net_sync::toggle_net_sync,
        hakotauri::net_sync::get_sync_status,
        hakotauri::net_sync::list_network_peers,
        hakotauri::net_sync::prepare_sync_restore,
        hakotauri::net_sync::bootstrap_sync,
        hakotauri::cloud_sync::toggle_cloud_sync,
        hakotauri::cloud_sync::get_cloud_sync_status,
        hakotauri::cloud_sync::get_cloud_peers,
        hakotauri::cloud_sync::get_cloud_config,
        hakotauri::cloud_sync::cloud_group_get,
        hakotauri::cloud_sync::cloud_group_new_key,
        hakotauri::cloud_sync::cloud_group_set,
        hakotauri::cloud_sync::cloud_group_add_member,
        hakotauri::cloud_sync::cloud_group_remove_member,
        hakotauri::cloud_sync::bootstrap_cloud_sync,
    ])
```

Use the **module path** (`gateway::hako_exec`), not the root re-export: the `#[command]` wrapper macro resolves through the same module as the function. The root re-export covers types and direct calls.

The gateway re-exports engine types (`Hako`, `HakoConfig`, `HakoDoc`, `Value`, `Query`, …), so Tauri backend code uses the same API as the [Rust core](crud.md) without a direct `hakodb` dependency. Pin sync planes explicitly with `default-features = false, features = ["net-sync", "cloud-sync"]` to stay immune to future default changes.

```ts
import { collection, doc, setDoc, getDoc, query, where, getDocs, onSnapshot } from "@hakodb/tauri";

await setDoc(doc(db, "users", "1"), { name: "alice" });
const snap = await getDoc(doc(db, "users", "1"));
const rows = await getDocs(query(collection(db, "users"), where("age", ">=", 18)));
const unsub = onSnapshot(collection(db, "users"), (docs) => render(docs));
```

Notes:

- Tauri `2.11` + `tauri-macros 2.6` + `tauri-runtime 2.11` are the supported line. The minor is unpinned on purpose so cargo unifies one Tauri version across the SDK and the consumer binary; two Tauri versions in one binary mean incompatible `State`/`Window` types and unregistrable commands.
- Watch subscriptions prebuild a filter plan once (`Hako::plan_for_watch`) and match per-event bytes with zero decode (`Hako::matches_watch`).
- Sync planes are opt-in features on the gateway (`net-sync`, `cloud-sync`, `socket-sync`): enable what the app needs; the TS side calls the same sync ops.
- `flushDatabase` / `listStorageKeys` cover the consumer ops (durability control, storage inspection).
- Graph and vector ops are wired through (`createTraverseIndex`, `findPaths`, `createEdgeIndex`, `findNear`).
- Deletes are soft by default: the `delete` op takes `force: true` for a hard delete, batch delete items carry per-item `force`, and `restore` / `restore_available` / `delete_queue` / `sweep` ops cover the retention surface (records come back under the `records` key).

## Common mistakes

- **Calling sync ops without enabling the feature.** The gateway compiles per-feature; a sync call against a gateway built without it fails at invoke time. Match features to calls.
- **Forgetting the gateway is per-window for listeners.** Window-scoped subscriptions die with the window — resubscribe on navigation, and clean up (`unsubscribe`) like any listener.
