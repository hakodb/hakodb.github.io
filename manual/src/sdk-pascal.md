# Pascal SDK (Lazarus / Free Pascal)

`hakodb/hakopascal` (currently `0.1.7`). Two units plus design-time components: `HakoRaw.pas` (direct `cdecl` imports from `hakodb.dll`), `Hako.pas` (friendly wrapper), `HakoCluster.pas` (cluster unit), installable `HakoComponent`/`HakoDesign` packages.

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

## Common mistakes

- **32-bit Lazarus target with the 64-bit DLL.** Link/load fails cryptically — match bitness first.
- **Forgetting `HakoCluster` needs the cluster DLL too.** The engine DLL alone doesn't provide the dispatcher symbols.
