# Cloud server deploy

One process, N+1 ports: the admin console plus one sync listener per room. Give every room its own port and keep the admin bind on loopback unless a reverse proxy terminates TLS in front.

## Services

- Linux: `contrib/hakocloudserver.service` (hardened systemd unit — `NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`, `ReadWritePaths` scoped to the rooms dir).
- Windows: `--install-service [--service-name NAME]` (requires absolute `--config`; auto-starts at boot), `--uninstall-service`. Stopping the service drains cleanly; NSSM remains a valid fallback.

Direct TLS for the admin console: `--tls-cert fullchain.pem --tls-key privkey.pem` (session cookies flip `Secure` automatically; HSTS follows). The sync plane stays `ws://` behind a reverse proxy, or terminate there too. Half a TLS pair refuses to boot — deliberate.

## Security posture

- Secrets live in the config file or `token_file`, never in argv/env; room keys and hub tokens never cross into logs or API responses.
- Never bind the console to `0.0.0.0` without TLS — the server logs a loud warning when it sees that combination.
- Sync traffic is plaintext `ws://`: terminate TLS at a reverse proxy (or run the hub on a trusted LAN) and rotate group API keys after any network you don't control sees them.
- Public probes (`/api/health`, `/api/setup/status`) expose room names plus one setup bit — names are handshake-visible on the sync plane anyway.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Refuses to boot naming a room | Bad name, missing secret, duplicate name/bind, or legacy single-db keys mixed in | Read the named reason; declare `[[rooms]]` cleanly |
| Client connects, room stays empty | Wrong `room_name`/`room_key` — rejected at handshake, nothing stored | Match the pair exactly |
| Console shows no admin prompt but login fails | Different room: each room has its own users | Create the admin in the room you log into |
| Rejected peer's data appears anyway | Check you are looking at the right room's console (sessions bind one room) | Re-login to the intended room and compare |
| Sync port unreachable from other hosts despite the process listening | Inbound firewall on the hub host | Allow the room's sync bind port; on DENY-by-default hosts with terminal `RETURN` rules, insert the ACCEPT before the chain's `RETURN` — an ACCEPT appended after it is never evaluated |
| Build from source fails inside a C library build script | A wedged ccache intercepting the compiler | Run the build with `CCACHE_DISABLE=1` |
