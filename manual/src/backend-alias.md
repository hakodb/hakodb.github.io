# Backend path aliases

Aliases are owner-declared rewrites: one client-friendly shape onto one target path + query. No scripts, no code.

```toml
[[aliases]]
pattern = "/api/alias/students/:sid/:pin"
target = "/api/collections/students"
query = "options={...{sid}...{pin}...}"
```

- Match is exact segments + `:param` captures only (no regex); first declaration wins.
- The request's own query **merges** (request wins on collision); `db` is alias-pinned and cannot be escaped.
- The rewritten request re-enters routing, so auth, policy, limits, and realtime see the **target** exactly like a direct call — one rule surface.
- Load-time guards refuse to boot on: pattern not under `/api/alias/`, target outside `/api/` or chaining into `/api/alias/`, unresolvable `{name}`, duplicates. Realtime lanes (`/ws`, `/api/stream/*`) cannot be targets.
- No match = empty 404, same as an unknown route.

## Common mistakes

- **Aliasing to hide policy.** Policy evaluates the target, so an alias never bypasses rules — but reviewers must read the target's rules, not the alias name. Name aliases after what they expose.
- **Regex-shaped expectations.** `:param` captures whole segments only; patterns needing regex belong in a real gateway, not here.
