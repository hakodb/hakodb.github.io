# Backend auth

The backend verifies; only the `local` provider issues tokens. Providers fill `AuthContext{uid, extra}` — policy rules never know which provider verified you.

```toml
# auth = "off"                  # anonymous (dev only)
# auth = "local"                # single issuer
# auth = "chain:github,local"   # try in order, first valid claims win
# auth = "./custom.toml"        # chain + declarative mapping
```

| Provider | Role | Needs |
|---|---|---|
| `local` | The only issuer: `/api/auth/register\|login\|refresh\|logout\|me`, dual-token BFF (short access JWT + rotating refresh, `__Host-` cookies) | `UB_LOCAL_JWT_SECRET` (32+ chars) |
| `firebase` | Verifier (Google JWKS) | `UB_FIREBASE_PROJECT` |
| `github` | Verifier + OAuth BFF login flow | `UB_GITHUB_CLIENT_ID` + secret (+ `local` in chain for sessions) |
| `oidc` | Verifier | `UB_OIDC_ISSUER` (+ audience) |
| `custom` | Mapping file (`uid_field`, `email_field`) over builtins | `./custom.toml` |

Unknown provider names fail fast at startup. UIDs are namespaced (`github:123`, `local:abc`) so providers never collide. Token attrs (`[identity].attrs`, e.g. `role`) are copied into the JWT at login/refresh — one read at issuance, zero per request — and fuel `claim:`/`fields:` policy rules (external providers get them differently — see below).

## Where role/status live on each provider

- **`local`** mints the allowlisted attrs into the JWT at login/refresh (server-minted; signup cannot self-assign them).
- **External verifiers** (firebase/oidc/github) carry two interchangeable sources — both feed `claim:` rules the same way:
  - **IDP custom claims** (zero backend config): whatever the identity provider minted (e.g. roles set in its admin console/API) passes through on verify. Values change when the token is re-issued.
  - **Server-side enrichment** (dynamic fields): after verify, the allowlisted `[identity].attrs` fields are read from the caller's user doc in `[identity].users_collection` (keyed by the namespaced uid) and override their token counterparts. Doc wins per field; no doc or missing field = token claim stands; no auto-provisioning. A short TTL cache keeps it at one user-doc read per minute per user — role edits apply within that window, no re-issue. `local` tokens skip enrichment (already minted); a reload flushes the cache.

Both sources coexist; docs win when they carry the field, so deployments can start with IDP claims and move them into the database without touching rule syntax.

Clients send `Authorization: Bearer …` (API) or the cookie (browser BFF). No token = anonymous; **policy decides**, not the middleware (unknown token + deny rule = 403, not 401 theater).

Hardening available: DPoP (`UB_LOCAL_DPOP` / `dpop`: `off|accept|require`) binds local tokens to a client key; service keys (`[service]`, loopback-only Bearer + scope list) cover co-hosted consumers without user identity; TLS via `--tls-cert/--tls-key` (rustls + HSTS).

## Common mistakes

- **`claim:` rules with external-only providers and no claim source.** They silently deny (nothing to match). Either mint roles as IDP custom claims, put the fields in the caller's user doc (`[identity].attrs` + `[identity].users_collection`), or add `local` to the chain.
- **Long-lived access tokens.** Access lives out its TTL even after logout (refresh is what revokes). Keep access 5–15 minutes and rotate refresh.
- **Secrets in config files.** Provider params are env-only. Config files are for structure, never secrets.
