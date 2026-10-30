# Pascal SDK (Lazarus / Free Pascal)

`hakodb/hakopascal`. Two units plus design-time components: `HakoRaw.pas` (direct `cdecl` imports from `hakodb.dll`), `Hako.pas` (friendly wrapper), `HakoCluster.pas` (cluster unit), installable `HakoComponent`/`HakoDesign` packages.

Put `hakodb.dll` next to your binary, on `PATH`, or under `./native/`. Populate `native/` with the sync script; binaries there are git-ignored:

```powershell
# from a local core checkout (build it first: cargo build --release)
.\sync-native.ps1 -CoreDir C:\Dev\libs\hakodb
# or from a core release (pass the tag you want)
.\sync-native.ps1 -Tag <core-release-tag>
```

The wrapper ships as two Lazarus packages, the standard runtime/designtime split:

- `HakoPkg.lpk` — runtime: `HakoRaw`, `Hako`, `HakoComponent`. Add it via Project Inspector → Add → New Requirement to use the SDK from code.
- `HakoDesign.lpk` — designtime (requires `HakoPkg`): `HakoPkgReg` with the `Register` procedure. Open via `Package > Open Package File (.lpk)`, Compile, then **Install** — a **HakoDB** tab with `THakoComponent` appears on the component palette.
- `HakoComponent.pas` — drop-on-form component. Sync is opt-in: `NetSyncEnabled` / `CloudSyncEnabled` default to False (`StartNetSync` / `StartCloudSync` raise otherwise).

```pascal
uses Hako;
var Eng: THako; Doc: THKDocument;
begin
  Eng := THako.Create('./data');
  try
    Doc := THKDocument.Create;
    try
      Doc.InsertStr('name', 'alice');
      Doc.InsertInt('age', 30);
      Eng.Collection('users').Doc('1').SetDoc(Doc);
    finally
      Doc.Free;
    end;
  finally
    Eng.Free;
  end;
end;
```

Notes:

- `hakodb.dll` (64-bit) must sit next to the executable or on `PATH`; `native/` in the repo carries the current pair (`hakodb.dll` + `hakocluster.dll`).
- Same rule as Go: every created handle is freed explicitly — `try/finally` is the pattern, not an option.
- References, graph (`CreateTraverseIndex`/`FindPaths`, `CreateEdgeIndex`/`ShortestPaths`), and vector (`CreateVectorIndex`/`FindNear`) mirror the C ABI one-to-one; when in doubt, `HakoRaw.pas` shows the exact import signature.
- Deletes are soft by default (`Doc(...).Restore` undoes while the record is queued); `RestoreAvailable`, `DeleteQueue`, and `SweepNow` expose the retention surface.

## Common mistakes

- **32-bit Lazarus target with the 64-bit DLL.** Link/load fails cryptically — match bitness first.
- **Forgetting `HakoCluster` needs the cluster DLL too.** The engine DLL alone doesn't provide the dispatcher symbols.
