# Sync encryption posture

Read this before encrypting anything that syncs. At-rest encryption and sync-time plaintext are **independent properties**: sync tailers read through the storage decryption layer and emit decoded documents, so an encrypted collection replicates as **plaintext on the wire** unless the rules below refuse the transfer. There is deliberately no silent path.

## What is (and isn't) protected

| Threat | Status |
|---|---|
| Disk / backup theft on any node | Protected when the node holds the key. |
| Keyless or wrong-key peer receiving your encrypted docs | **Refused, loudly**, both directions. |
| Old (pre-capability) peer in the room | Encrypted rooms pause for it; plaintext rooms keep syncing. Upgrade to resume. |
| Server operator / DB thief | **Not protected.** The hub needs room keys in the clear to route. |
| Passive LAN observer | **Not protected.** Use `wss://`/mTLS segments or end-to-end rooms. |
| Active impersonator replaying a fingerprint | **Not protected.** Fingerprints are assertions (key hash), not proofs. Mitigated by admission + room keys. |

Admission control (groups, API keys, room keys) decides *who may join*; these rules decide *what may leave*.

## How it works

Every handshake carries encryption capabilities: mesh `SyncCaps` (`key_fp` = SHA-256 of the at-rest secret + encrypted collection list) after `Identify`; cloud `enc_fp`/`enc_cols` on `Authenticate`. One rule everywhere (`caps_allow`): a locally-encrypted collection flows **iff** the peer presented the same non-zero fingerprint. Everything else — old, keyless, wrong-key — is refused per collection with a throttled loud warning naming peer and collection. Catch-up re-sends anything skipped once caps arrive.

## Operating it

1. Same `encryption_key` on every node sharing the room; list it in `encrypted_cols` (empty = global). Names are plain everywhere - server and client use the same collection names.
2. Expect `[sync-guard]` warnings while any peer is keyless, wrong-keyed, or old — fix by distributing the key or upgrading, never by relaxing.
3. There is intentionally **no override flag**. Mixed-version rooms keep working for plaintext throughout the upgrade.

## Common mistakes

- **Assuming encryption = end-to-end.** At-rest keys protect disks, not wires or operators. If the hub operator must not read a room, that room needs E2E encryption (future work), not at-rest keys.
- **Rotating keys without a plan.** A new key is a new fingerprint: rooms partition until every node carries it. Rotate room by room, never fleet-wide at once.
