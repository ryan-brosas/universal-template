<!-- capsule-v2 -->
# LTAR text↔link conversion — how does a text column become a link field (and back) synchronously without corrupting meta cache, undo, or the related table's UI?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the exact ordering contract of snapshot → create → delete → rename → backfill that makes an in-request schema+data transformation both reversible and observable?

## Factory-closure conversion ops with replay-aware side-effect capture

**Path/Symbol:** `packages/nocodb/src/helpers/ltarColumnConversion.ts:ltarColumnConversion` factory (:49–1038) returning `{convertSingleLineTextToLtar (:233–468), convertLtarToSingleLineText, revertLinkColumnToText, revertTextColumnToLink}`; helpers `broadcastColumnConversion` (:60–124), `broadcastRelatedTableBackLink` (:134–173), `assertConvertibleRowCount` (:188–213), `backfillLtarFromText` (:474–…).
**Signature:** `(svc: IColumnConversionHost) => ({...ops})` — the `baseModelInsert` factory pattern: service passes itself as host; ops close over it.
**Data Shape:** Snapshot rows `{pk: string|number, text: string}[]`; `textColumnSnapshot` is a hand-rolled 17-field record (id/fk_model_id/column_name/title/uidt/dt/dtxp/dtxs/np/ns/clen/ct/cdf/rqd/un/meta/order) so undo can recreate the column exactly; side-effect ids captured via `_ltarCapture` + replay scope keys `convertedLinkId`, `columnBackupOut`.

### Decisive source
```ts
// :32-40 — the two load-bearing constants
const LTAR_CONVERSION_MAX_ROWS = 5_000;
// Lowercase alphanumeric — safe inside a PG identifier when concatenated.
const tempTitleSuffix = customAlphabet('abcdefghijklmnopqrstuvwxyz0123456789', 8);
```

**Flow (text→link):** cap check (`assertConvertibleRowCount` — text→link counts only non-blank source cells via a `notblank` Filter; SKIPPED under `isReplay()` because redo must always finish and forward already enforced the cap) → paged snapshot read (PAGE=1000, `ignoreViewFilterAndSort`) skipping null/blank cells → data backup (`columnDataBackupHandler.backup`, failure only downgrades undo support, never aborts) → create LTAR under TEMP title `${originalTitle}_link_<8-char>` with colBody identity fields STRIPPED (id/column_name/fk_model_id/fk_column_id/colOptions/order destructured away so a fresh column is created instead of reusing the source's id) → hard-delete source (`skipTrash: true` because undo recreates with the SAME id — data survives in the backup, not trash) → rename LTAR to original title BEFORE backfill (**ordering invariant pinned in-comment**: schema steps recompute columnsHash; running them before backfill keeps the hash off meta-cache state that record reads churn — "can transiently leave lazy-loaded promises on cached models and crash object-hash") using `isSimpleUpdate: true` (full Column.update would re-process the LTAR relationship) → backfill links append-only via display-value→pk resolution in chunks of 200, unmatched values skipped, single-link relations take first match → best-effort broadcasts: COLUMN_UPDATE to source table + column_add back-link notice to related table (skipping self-relations). **Serialization armor:** both broadcasters JSON-round-trip table/column payloads through a WeakSet seen-set replacer because "the new relation can make the loaded column graph circular" — broadcasting raw instances blows the stack (junction-less hm/bt pair restore case, :88–95).
**Invariant:** (1) Sub-ops get FRESH `reuse: {}` handles — sharing the caller's mutated Model/baseModel through `reuse` pollutes the meta cache and breaks `hash(columns)` (:265–270 comment). (2) The hm/bt pair-restore path (`reverseRestore`) renames BOTH columns and backfills onto the REVERSE (bt) column — the saved one keeps its own captured title. (3) Broadcast failures are logged warnings AFTER commit — notification must never abort a committed schema change.

### Porting traps (each verified against source)
- Undo of junction-less bt→text re-enters convertSingleLineTextToLtar with `reverseRestore` AND `setReplay('convertedLinkId', link.id)` so redo recreates the same link id (:966–973 region).
- In-file anchors: `grep -c 'LTAR_CONVERSION_MAX_ROWS' src/helpers/ltarColumnConversion.ts` → 4; `grep -c 'isReplay()' …` → 3; `grep -n 'crash' …` → :404 region (object-hash comment); `grep -c 'skipTrash: true' …` → 1.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n 'LTAR_CONVERSION_MAX_ROWS =' src/helpers/ltarColumnConversion.ts | cut -d: -f1` → `32` and `sed -n '398,405p' src/helpers/ltarColumnConversion.ts | grep -c 'columnsHash'` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "ltarColumnConversion convertSingleLineTextToLtar LTAR_CONVERSION_MAX_ROWS", limit: 10 });
```
Resolves `convertSingleLineTextToLtar` :233-468 rank-1, factory :49-1038 rank-2, service delegator `ColumnsService.convertSingleLineTextToLtar` :6405-6426 rank-3.

## Verdict
Adopt the five-step ordering (snapshot→create-temp→hard-delete→rename-before-backfill→backfill), fresh-reuse-per-subop rule, temp-title alphabet, circular-safe broadcast cloning, and replay-bypass semantics for the row cap; adapt the 5,000-row budget to host; omit nothing silently. Coverage caveat: no direct tests at pin; probes are source-greps.
