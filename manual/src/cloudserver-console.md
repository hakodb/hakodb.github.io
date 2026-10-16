# Cloud server console

The admin plane (`admin_bind`) serves a dependency-free web console and a JSON API. First run: the setup wizard lists the declared rooms — pick one and create its initial administrator. Each room has its own users; the wizard stays reachable until every room has an admin.

## Sessions bind to one room

Login and setup both name their room, and the session cookie is bound to it: every later call with that cookie is scoped to that room. One session can never touch two rooms; switching rooms means re-login. A session whose room is gone fails closed instead of falling back.

Roles: `viewer` (read), `operator` (read + write data), `admin` (everything including users, groups, maintenance). Login brute-force keeps its own strict per-IP counter; the whole plane has a generous global ceiling.

## What the console manages

- **Data**: collections, query, document get/put/patch/delete, atomic batches, indexes (simple/FTS/composite), stats.
- **Groups**: sync admission policy per room. Absent groups admit everyone (open by default); `registered` mode issues an API key — shown once, only its hash persists — that peers present at handshake, optionally plus a member allowlist. Rotate or destroy the hash in one click.
- **Users**: per-room accounts with Argon2id hashes; create/disable/delete with last-admin protection (no self-demote, no self-delete, no deleting the final admin).
- **Events**: one SSE stream per connection scoped to the login room — document pumps for watched collections, peer membership diffs, and version-clock diffs, with an initial snapshot so the UI renders immediately.
- **Maintenance**: absolute-path-only backups, compact, per-collection vacuum.

Internal collections (`__users`, `__groups`, anything `__`-prefixed) are never addressable over the data plane — even for operators — and the sync token/key material is never serialized anywhere.
