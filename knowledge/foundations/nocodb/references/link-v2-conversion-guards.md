<!-- capsule-v2 -->
# V2-link conversion guards — which pre-dispatch rejections prevent one-sided V2 upgrades from corrupting both sides?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Before converting a V1 Link/LTAR column to V2 junction-based storage, what must be refused so a partially-converted relation can't compound damage?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/services/columns.service.ts:findPairedLinkColumn` (:7915–:7957) + `convertLinkToV2` guards (:7982–:8028).
**Signature:** `protected findPairedLinkColumn(context, column: Column, colOptions: LinkToAnotherRecordColumn): Promise<Column | undefined>`.
**Data Shape:** MM-family match = same `fk_mm_model_id` ∧ SWAPPED fk columns (`opts.fk_mm_child_column_id === colOptions.fk_mm_parent_column_id` and vice versa — handles self-referencing tables); direct HM/BT/OO match = equal `fk_parent_column_id` ∧ `fk_child_column_id`.

### Decisive source
```ts
// System columns (auto-created HM links to junction tables, etc.) are
// hidden in the UI and must never be upgraded — calling convertLinkToV2
// on them corrupts the junction-side metadata of the parent M2M.
if (column.system) { NcError.badRequest('Cannot upgrade a system column.'); }
// Reject when the paired column on the other side of the relation is
// already V2 but this column is V1. Both sides must transition together —
// an earlier convert call mutated only one side, and re-running here would
// create duplicate Rollup/LTAR metadata and corrupt dependent references.
```

**Flow:** reject system columns → reject any column living ON a junction table (`ownerModel?.mm`) → if this column still V1, scan the RELATED table's link/LTAR columns via findPairedLinkColumn (skipping self, matching relation shape) → if the pair is already V2, badRequest telling the caller BOTH sides transition together and manual repair may be needed instead of compounding metadata corruption.
**Invariant:** (1) A relation has TWO link columns; version flips must be atomic across both — detecting the half-flipped state and FAILING LOUDLY beats repairing in place. (2) Junction-side matching requires FK-column swap or self-referencing tables match themselves. (3) The helper is read-only and dispatches BEFORE convertMMToV2/convertHmToV2 etc., whose internal paired-finding stays in place — no behavior change for already-consistent conversions. (4) System columns are auto-created HM links into junction tables; upgrading them corrupts the parent M2M's junction-side metadata even though they're invisible.
**Probe:** `grep -n "version !== LinksVersion.V2" …columns.service.ts` → :8007; `sed -n '7915,7957p'` full helper verified. No upstream unit suite (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "convertLinkToV2 findPairedLinkColumn LinksVersion guard", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-guard pre-dispatch ladder + swapped-FK pairing; adapt error surfaces; omit if host has single-sided link storage.
