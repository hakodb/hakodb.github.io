# Backend policy

One global file (`policy.toml`, hot-reloaded), evaluated on collection names for every verb. Copy `policy.standard.toml`, then open per collection.

```toml
[identity]
users_collection = "users"     # free choice; attrs below ride token claims
attrs = ["role", "department"] # local-issuer only (see caveat)

[defaults]
read = "deny"
write = "deny"

[collections.posts]
read = "public"                # anyone reads
create = "auth"                # any authenticated caller writes
update = "auth"
delete = "auth"

[collections.profiles]
read = "auth"
write = "auth"

[collections.ai_configs]       # credentials: deny, open explicitly per app
read = "deny"
write = "deny"
```

Resolution: method slot → alias read/write → exact collection → root segment → `[defaults]` → deny. `posts/p1/revisions` falls back to `posts`, never to a last-segment guess.

Rule vocabulary: `public` (anyone), `auth` (any authenticated caller), `deny` (nobody), `claim:role=editor` / `claim:uid=self` (token claims), `fields:unit=auth.unit,score=int:0..100` (scoped + typed writes). Admin = caller UID in server `admin_uids` — UIDs, not roles. `__`-prefixed collections are never addressable over HTTP.

Claim caveat: `[identity].attrs` mint into tokens **only via the local issuer**. External providers (firebase/github/oidc) never mint user-doc attrs — `claim:` rules on them silently deny (boot warns). Those deployments put roles in JWT custom claims instead.

Error contract: policy reject is always `403 Permission denied by policy` — never which rule failed. Missing doc 404, wrong route kind 400, duplicate `already-exists`, rate-limit 429.

## Common mistakes

- **Leaving `[defaults]` open.** Start deny/deny; open collection by collection. The standard template already does this.
- **Per-user separation via clever rules.** Separation is data modeling (separate collections) or an external tenant layer — not rule gymnastics.
- **Expecting `owner` semantics for free.** Ownership of existing docs is id-match (`claim:uid=self`); anything needing change-detection is out of scope — use strips/field rules instead.
