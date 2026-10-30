# Go SDK

Module `github.com/hakodb/hakogo` (package `hako`, repo `hakodb/hakogo`). cgo bindings over the C ABI with a fluent document layer.

Populate `third_party/` (canonical `hakodb.h` + platform binary) with the repo's sync script. Headers are committed; binaries under `third_party/lib/` are git-ignored. `go build`/`go vet` need a C compiler on `PATH` (MinGW gcc on Windows).

```powershell
# from a local core checkout (build it first: cargo build --release)
.\sync-core.ps1 -CoreDir C:\Dev\libs\hakodb
# or from a core release (pass the tag you want)
.\sync-core.ps1 -Tag <core-release-tag>
```

```sh
./sync-core.sh --core-dir /path/to/hakodb
./sync-core.sh --tag <core-release-tag>
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
- Deletes are soft by default (restoreable until the sweeper purges the retention record); the retention surface is wrapped (`Restore`, `RestoreAvailableJSON`, `DeleteQueueJSON`, `SweepNow`) and force deletes are explicit.
- Cross the boundary with JSON where convenient (`ownedCStringJSON` helpers) and handles where hot.

## Common mistakes

- **Missing `defer …Free()` in loops.** One leaked doc per iteration is a slow memory bleed that only shows up in production. Allocate outside the loop or free inside.
- **Mixing 32/64-bit.** The shipped DLL is 64-bit; build the Go binary for `amd64`, or cgo fails at link time with an unhelpful message.
