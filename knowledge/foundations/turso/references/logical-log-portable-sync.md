<!-- capsule-v2 -->
# MVCC portable logical sync — how do you mark which log frames are replayable by an OUTSIDE engine without breaking old readers?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When a sync consumer must distinguish "no user-visible change" from "change I cannot decode", what frame/header versioning makes that possible and backward-safe?

## LML2 vs LML3 header gating + always-emit portable extension blocks
**Path/Symbol:** `core/mvcc/persistent_storage/logical_log.rs:296-300` (`LOG_MAGIC 0x4C4D4C32 "LML2"`, `LOG_VERSION_V2 = 2`, `LOG_VERSION = 3`), first-write version choice :727-737, upgrade gate `upgrade_header_for_log_tx` :901+, extension rationale :707-720, `TX_EXT_HEADER_SIZE` insertion :738-748, name partitioning `is_portable_logical_name` (`mvcc/portable_logical.rs:24-30`).
**Signature:** `fn is_portable_logical_name(name) -> bool` — excludes `sqlite_*`, `__turso_internal_*`, `turso_sync_*`, `turso_cdc*` / `turso_cdc_version`.
**Data Shape:** non-portable logs stay V2 so a deployment without portable extensions can roll back to V2-only readers; portable frames carry an extension block after the main payload flagged by `OP_FLAG_PORTABLE_EXTENSION` ("Recovery may ignore those bytes, but the parser must consume them as part of the op").

### Decisive source
```rust
// :712-719 — why emit even when empty:
// Every commit from a portable-enabled writer gets an extension block,
// including one whose portable object map is empty. A transaction that
// touches only internal objects ... would otherwise be written as a plain
// frame ... byte-identical to pre-portable LML2 history: a reader planning a
// logical sync range cannot tell "no user-visible changes here" from "user
// data this reader cannot replay", so it must refuse the range.
```
That comment is the whole design: absence-of-extension is ambiguous, so presence must be unconditional under the feature. The upgrade path refuses mid-log upgrades ("portable logical changes require logical log header upgrade before append") — version flips only at offset 0. Portable schema rows materialize from decoded `sqlite_schema` records (type/name/rootpage, ≥5 columns asserted) into a stable object map keyed by the same name filter.

**Flow:** writer enables portable → first write stamps LML3 header → every tx appends ext block (possibly empty) → external reader decodes user-visible ops by name filter → legacy reader consumes-but-ignores ext bytes on V3?? — no: legacy readers never see V3 because mixed fleets pin the header at V2 until ALL writers upgrade.
**Invariant:** format-version flips only on empty log; ambiguity between "nothing to sync" and "cannot sync" must be impossible; internal-object writes never masquerade as portable changes.
**Probe:** in-file tests: `test_non_portable_first_write_uses_lml2_header_and_v2_frame`, `upgrade_header_for_log_tx` unit paths, `test_encrypted_log_format_assumptions_are_pinned`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "portable_changes LOG_VERSION_V2 is_portable_logical_name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt explicit-presence markers for any capability-signaled log format consumed by heterogeneous readers. Adapt name-partition prefixes to your catalog. Omit encryption interplay unless shipping both features.
