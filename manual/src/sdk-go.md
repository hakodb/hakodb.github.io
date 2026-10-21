# Go SDK

Module `github.com/hakodb/hakogo` (package `hako`, repo `hakodb/hakogo`, currently `0.1.9`). cgo bindings over the C ABI with a fluent document layer.

Populate `third_party/` (canonical `hakodb.h` + platform binary) with the repo's sync script. Headers are committed; binaries under `third_party/lib/` are git-ignored. `go build`/`go vet` need a C compiler on `PATH` (MinGW gcc on Windows).

```powershell
.\sync-core.ps1 -CoreDir C:\Dev\libs\hakodb
.\sync-core.ps1 -Tag v0.16.7
```

```sh
./sync-core.sh --core-dir /path/to/hakodb
./sync-core.sh --tag v0.16.7
```

```go
import "github.com/hakodb/hakogo/hako"

eng, err := hako.Open("./data")
if err != nil { log.Fatal(err) }
defer eng.Close()

doc := hako.NewDoc()
defer doc.Free()
doc.InsertString("name", "alice")
doc.InsertInt("age", 30)
if err := eng.Set("users", "1", doc); err != nil { log.Fatal(err) }

got, err := eng.GetDoc("users", "1")
if err != nil { log.Fatal(err) }
defer got.Free()
```

Patterns:

- Every handle (`Engine`, `Doc`, `Query`, `Batch`, `Config`, `Array`) has an explicit `Free`/`Close` — `defer` it at creation. No finalizers; leaks are silent.
- Errors come back as Go `error` (check `err`, then `hako.LastError()` detail lives inside already).
- Queries: `NewQuery(collection)` + `Where*` builders + `Execute`; graph via `CreateTraverseIndex`/`FindPaths`, `CreateEdgeIndex`/`ShortestPaths`; vector via `CreateVectorIndex`/`FindNear`.
- Cross the boundary with JSON where convenient (`ownedCStringJSON` helpers) and handles where hot.

## Common mistakes

- **Missing `defer …Free()` in loops.** One leaked doc per iteration is a slow memory bleed that only shows up in production. Allocate outside the loop or free inside.
- **Mixing 32/64-bit.** The shipped DLL is 64-bit; build the Go binary for `amd64`, or cgo fails at link time with an unhelpful message.
