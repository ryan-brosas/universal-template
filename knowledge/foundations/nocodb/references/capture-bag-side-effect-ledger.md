<!-- capsule-v2 -->
# CaptureBag side-effect ledger — what typed slots must an undoable operation record so its inverse can replay without re-deriving anything?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What is the complete typed contract for trace captures, and which invariants make undo/redo id-stable?

## 21-key typed capture bag + macro transcript
**Path/Symbol:** `packages/nocodb/src/command-registry/types.ts:CaptureBag` (:247–:369, 21 top-level keys) · `MacroTranscriptEntry` (:196–:240) · `OperationContract` (:21–:54) · `DisplacedRecord`/`LinkChange` (:371–:430).
**Signature:** values deposited via `captureForTrace(key, value)` (CE no-op; EE stores per-call), persisted via `contract.capture: [key...]` + strict `capture_schema`; read back through `HandlerMeta.extra`.
**Data Shape:** highlights — `ltar: LtarSideEffectIds`, `convertedLink {linkColumnId, textColumn}`, `convertedText {textColumnId}` (redo recreates with SAME id), `viewSectionViewIds`, `baseSectionChildren` (carries `order` too — section delete rewrites children's orders to fill the gap), `linkSwapEntry|null`, `macroTranscript[]`, `recordPrev[]` (pre-mutation row snapshots, order-matched to input), `displacedRecords` (column vs junction variants), `recordModelContext {modelId, primaryKeyTitles}` (survives renamed-base lookups), `softDeleteTrashId`, `upsertChanges` (update carries prev; insert rides rotated trashId).

### Decisive source
```ts
/** Entities that lived in a base-level section at delete time. Unlike view
 *  sections this must carry `order` too: deleting a base section rewrites its
 *  children's orders to fill the gap it leaves, so re-linking alone would
 *  restore the grouping but not the positions. */
baseSectionChildren: ReadonlyArray<{
  id: string;
  entity: 'table' | 'document' | 'dashboard';
  order?: number;
}>;
```
(:316–:325)

**Flow:** forward op runs inside @TraceCommand → deposits side-effect ids at creation points (no extra lookups later) → decorator persists chosen keys as `meta.extra` on operation-log/sandbox rows → inverse builders construct InverseOp from captured ids (undo) or re-apply (redo) → macro ops auto-append one MacroTranscriptEntry per nested traced child (params post-NON_SERIALIZABLE_KEYS filter, resolvedExtra = child's before() snapshot, entityId for trash-restore short-circuit); replay iterates the transcript via OperationRegistry instead of re-running the service body.
**Invariant:** capture-at-creation-point is the rule — every doc comment says "captured at the point of insertion (no extra lookup)" because later lookups fail after renames/deletes. Id PRESERVATION beats re-creation: convertedText/convertedLink/sandboxColumns exist so redo reuses original ids; pk preservation on upsert-inserts matters because re-running upsert mints new auto-pks. `version` bump invalidates old changelog rows (name@version is the registry key AND the changelog event column).
**Probe:** `cd packages/nocodb && awk '/^export interface CaptureBag/,/^}/' src/command-registry/types.ts | grep -cE "^  [a-zA-Z]+:"` (=21 keys) and `grep -n "readonly macro?: boolean" src/command-registry/types.ts` (:52 single declaration).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "CaptureBag MacroTranscriptEntry DisplacedRecord LinkChange OperationContract", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the typed-capture-bag pattern with capture-at-creation discipline; adapt keys to your side effects; omit macro/sandbox arms if you ship no undo surface (then also omit TraceCommand stubs). Coverage caveat: CE half is type-only + no-op stubs; consumer logic lives in EE overrides not present in this clone.
