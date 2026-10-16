# Cloud server configuration

One file, `--config /etc/hako-cloud/hako-cloud.toml` (`./hako-cloud.toml` auto-loads when present; legacy `./firelite-cloud.toml` still honored). Layers, lowest wins last: compiled defaults < file < `HK_*` env (`HK_ADMIN_BIND`, `HK_LOG_LEVEL`, `HK_SECURE_COOKIES=1`, `HK_SERVER_ID`, `HK_TLS_CERT`, `HK_TLS_KEY`; pre-rebrand `FL_*` still works as fallback) < CLI flags.

`[[rooms]]` is file-only — lists don't merge sanely across layers, so there are no env/CLI per-room overrides. Legacy single-db keys (`db_path`, `sync_bind`, `sync_token*`) are refused outright: a 0.x config must not boot against the rooms model with half its meaning silently dropped.

## Minimal file

```toml
admin_bind = "127.0.0.1:8081"
rooms_dir = "/var/lib/hako-cloud/rooms"

[[rooms]]
name = "field-team"
key = "room-secret-see-op-notes"
token = "hub-secret-clients-present-this"
sync_bind = "0.0.0.0:8080"

[[rooms]]
name = "hq"
key = "another-room-secret"
token_file = "/run/secrets/hako-hq-token"
sync_bind = "0.0.0.0:8081"
```

## Room fields

| Field | Meaning |
|---|---|
| `name` | `1..=64` chars, `[A-Za-z0-9_-]`, no `__` prefix. Directory name is an opaque hash of name+key, never the plain name. |
| `key` | Room membership credential presented at handshake. Mismatch is a handshake reject, fail-closed. |
| `token` / `token_file` | Hub secret for the room (clients present it as auth token). Exactly one required; files keep secrets out of argv/env. |
| `sync_bind` | Listener address for this room. Each room needs its own port — one listener per room, no dispatcher. |

## Validation (fail-closed)

Empty room list, bad names, missing secrets, duplicate names, and duplicate binds all refuse boot with a named reason. Same name + same key reopens the same directory (resume); the same name twice in one file is a hard error, never a silent overwrite.
