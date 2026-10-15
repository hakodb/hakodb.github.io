# Backend deploy

The artifact is a static musl binary — same file on EL7/EL8/ubuntu/Alpine. Deploy = binary + TOML + data dir + systemd.

```ini
# /etc/systemd/system/hakobackend.service
[Service]
User=hako
WorkingDirectory=/srv/hakobackend
ExecStart=/srv/hakobackend/hakobackend --config /srv/hakobackend/hakobackend.toml
Restart=on-failure
```

Checklist:

1. **Config**: copy `hakobackend.example.toml` → set `driver`/`data`, `auth`, `admin_uids`, `rules` (start from `policy.standard.toml`, deny-by-default). No secrets in the file — env only.
2. **Data dir**: owned by the service user, on a volume with headroom (alert 80%). SQLite/hako files live here.
3. **Smoke**: `/api/ready` → `{"ready":true}`. Then one authenticated write + read through policy (proves auth→policy→driver, not just TCP).
4. **Reload vs restart**: policy/auth/DB/limits/indexes/aliases → `POST /api/admin/reload`. Port/TLS/socket → restart.
5. **Backups**: stopped file copies (or `backup` semantics) on a schedule; verify restores quarterly; monitor backup age.
6. **Monitor**: `/api/ready`, disk space, backup age. Pair `ready` with those three or you will learn about full disks from users.

Upgrades: download the new tarball → verify SHA → backup binary + data → atomic install → restart → smoke → rollback restores previous bytes on failure. (This is exactly what `deploy-release.sh` automates where present.)

## Common mistakes

- **Running as root with a world-writable data dir.** Service user, `750` dirs, `640` configs. Secrets in env, not files.
- **Skipping the authenticated smoke.** `ready:true` with broken policy means "serving denials". One authed write+read closes the loop.
- **Forgetting the reload port.** Changing policy and waiting for it to apply without calling `/api/admin/reload` — the file is read on reload, not watched.
