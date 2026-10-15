# Backend auth

The backend verifies; only `local` issues. Providers fill `AuthContext{uid, extra}` — policy rules never know which provider verified you.

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

Unknown provider names fail fast at startup. UIDs are namespaced (`github:123`, `local:abc`) so providers never collide. Token attrs (`[identity].attrs`, e.g. `role`) are copied into the JWT at login/refresh — one read at issuance, zero per request — and fuel `claim:`/`fields:` policy rules.

Clients send `Authorization: Bearer …` (API) or the cookie (browser BFF). No token = anonymous; **policy decides**, not the middleware (unknown token + deny rule = 403, not 401 theater).

Hardening available: DPoP (`UB_LOCAL_DPOP` / `dpop`: `off|accept|require`) binds local tokens to a client key; service keys (`[service]`, loopback-only Bearer + scope list) cover co-hosted consumers without user identity; TLS via `--tls-cert/--tls-key` (rustls + HSTS).

## Common mistakes

- **`claim:` rules with external-only providers.** They silently deny (no attrs minted). Either add `local` to the chain or mint roles as JWT custom claims.
- **Long-lived access tokens.** Access lives out its TTL even after logout (refresh is what revokes). Keep access 5–15 minutes and rotate refresh.
- **Secrets in config files.** Provider params are env-only. Config files are for structure, never secrets.
