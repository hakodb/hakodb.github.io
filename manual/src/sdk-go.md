# Go SDK

Module `github.com/hakodb/hako-go` (`hakodb/hakogo`, currently `0.1.7`). cgo bindings over the C ABI; the Windows DLL ships under `third_party/lib` (other platforms: point cgo at a local release asset).

```go
import "github.com/hakodb/hako-go/hako"

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
