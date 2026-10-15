# Backend configuration

Precedence: **CLI flags > config file > defaults** (`--help` lists all flags). Start from `hakobackend.example.toml`.

```toml
host = "0.0.0.0"
port = 3000

# CHANGE DATABASE: edit 2 lines + POST /api/admin/reload. No rebuild.
driver = "hako"            # hako | hakocluster | sqlite | postgres | mysql | rethinkdb
data = "./data/hako.ub"    # path (hako/sqlite), comma-separated dirs (hakocluster), DSN (postgres/mysql)

# Socket peering with sibling backends (hako only, unix only, single-db):
# sync_serve = "/run/hakobackend/hako.sock"
# sync_peer = ["/run/other/hako.sock"]

auth = "off"               # off | local | chain:github,local | ./custom.toml
# admin_uids = ["local:root"]
rules = "./policy.toml"    # hot-reloaded; empty = OPEN dev mode (never prod)

[[indexes]]                # created at startup + reload; nothing is inferred
collection = "posts"
fields = ["age"]
kind = "simple"            # simple | composite | fts

limit_global = 600         # req/min per IP (+ _burst); /api/health always open
limit_auth = 20            # stricter layer for /api/auth/*
```

Notes:

- **Co-located SQL over unix socket** (measured much faster than TCP on weak CPUs): postgres `data = "postgres://user:pass@%2Fvar%2Frun%2Fpostgresql/dbname"`, mysql with `?socket=...`.
- **Multidatabase**: `[databases]` adds named DBs (`?db=` on every route); `data` is always `default`. Policy uses dotted names (`akademik.mahasiswa`, quoted in TOML).
- **Reload vs restart**: `POST /api/admin/reload` (admin UIDs only) picks up DB/auth/policy/limits/indexes. Port/listen/TLS/socket changes need a restart.
- **Secrets never live in config files**: provider params via env (`UB_LOCAL_JWT_SECRET` min 32 chars, `UB_FIREBASE_PROJECT`, `UB_OIDC_ISSUER`, …).

## Common mistakes

- **Production without `rules`.** Empty policy = open server with a WARN you stopped reading. Copy `policy.standard.toml` first, open later per collection.
- **`trust_proxy = true` without a stripping proxy.** Forged `X-Forwarded-For` then defeats rate limits. Default false; enable only behind your own proxy.
