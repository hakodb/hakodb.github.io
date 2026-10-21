# Operations

## Sizing

- **Memory**: hot set lives mapped; size RAM for the working set, not the database. `memory_limits` caps the inlined-RAM tier; the rest spills to segments.
- **Disk**: segments + WAL + index snapshots. WAL peaks under write bursts — reserve 2× your largest import batch plus headroom, and alert at 80%.
- **Workers**: `query_workers` scales parallel scans; the background indexer and compactor are already async. More threads help scans, not single-doc latency.

## Scaling the cloud hub

Single-process catch-up saturates the send+apply path; the knob that moves aggregate throughput is the number of independent serve points. Use one writer pod plus read-only replica pods on the same room, wired over the engine mesh: [Scaling writer pods and mesh replicas](scaling.md). For many LAN peers behind one cloud pull, use the manual relay: [LAN relay](lan-relay.md).

## Benchmarking before and after changes

Settle background work before measuring, and compare equal work. The harness, profiles, gate, and reference numbers are on the [Benchmarking](benchmarking.md) page.

## Upgrading versions

1. Read the CHANGELOG entry for the target version (wire/format notes live there).
2. Same-minor upgrades are drop-in. Across minors: mixed-version rooms keep syncing plaintext; encrypted rooms pause for old peers until upgraded.
3. Roll forward, not back: new files may carry formats old binaries can't read. Keep the previous binary + a backup until the new one is verified.

## Backup discipline

Automate `backup()` (or stopped file copies) on a schedule; verify restores quarterly by opening the backup copy. Monitor backup age alongside disk space — a backup job that silently stopped is the same as no backup.

## Troubleshooting FAQ

| Symptom | Check |
|---|---|
| Slow first query after restart | Index snapshot rebuild — expected; `is_indexes_ready()` tells you when done. |
| `Corrupt: Denied` everywhere | Security rules or missing key context, not data loss. Check policy + auth. |
| Sync stalled, no errors | Versions already converged (check `get_version_map` both sides) or an excluded collection. |
| Binary won't start after upgrade | Version/format note in CHANGELOG; restore backup + previous binary. |
| Mobile sync dies in background | OS suspension — foreground service / background modes, per platform. |

## When to ask for help

File issues with: versions (core + SDK), the full error string, the smallest reproduction (a `hakocli` command sequence is ideal), and whether sync is involved and which plane. "Slow" reports need `explain()` output and the durability mode.
