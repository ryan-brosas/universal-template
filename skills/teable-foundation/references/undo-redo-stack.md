<!-- capsule-v2 -->
# Versioned undo/redo command stack — how do you undo arbitrary write operations by REPLAYING commands instead of storing inverse patches?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does an undo entry stay replayable after schema changes, and which guard rails decide whether an append is even recorded?

## Command-replay stack with mode-gated appends and version gates
**Path/Symbol:** `packages/v2/core/src/application/services/UndoRedoStackService.ts`: append gates `appendEntry` (361–408), typed appends `appendRecordUpdate` (202+), `appendRecordUpdateFromSnapshot` (249+), `appendRecordDelete` (287+), `appendRecordCreate` (323+); replay `applyStackEntry` (440–491) via `applyUndo` (:414)/`applyRedo` (:431); command reconstruction `createCommand` (493–538) with version gate `ensureSupportedCommandVersion`; store contract `ports/UndoRedoStore.ts` (`composeUndoRedoCommands`, `isSupportedUndoRedoCommandVersion`, `undoRedoCommandVersions`, `UndoScope{actorId,tableId,windowId}`); snapshot→entry mapper `application/services/RecordMutationSnapshotContract.ts:toUndoRedoRestoreRecord`.
**Signature:** `appendEntry(context: UndoRedoStackAppendContext, tableId, entry: Omit<UndoEntry,'scope'|'createdAt'|'requestId'>): Promise<Result<void,DomainError>>`; `applyUndo(context: UndoRedoStackReplayContext, tableId, windowId?, options?): Promise<Result<UndoEntry|null,DomainError>>`.
**Data Shape:** `UndoEntry = {scope, createdAt ISO string, requestId, undoCommand: UndoRedoCommandData, redoCommand: UndoRedoCommandData}` where command data is `{type: 'UpdateRecord'|'UpdateRecords'|'DeleteRecords'|'RestoreRecords'|'ApplyRecordOrders'|'DeleteField'|'ApplyFieldSnapshot'|'ReplayFieldTypeConversion'|'Batch', payload, version}`; scope keys stacks per actor+table+browser-window.

### Decisive source
```ts
// THE append gate — three silent no-op conditions:
async appendEntry(context, tableId, entry) {
  if (context.stackMode === 'undo' || context.stackMode === 'redo') return ok(undefined);
  if (!context.windowId) return ok(undefined);
  if (this.isEmptyCommand(entry.undoCommand) && this.isEmptyCommand(entry.redoCommand))
    return ok(undefined);
  ...
}
// Replay = pop from store, rebuild a REAL command, re-dispatch through the bus:
const commandData = mode === 'undo' ? entry.undoCommand : entry.redoCommand;
const executeContext = service.buildReplayExecutionContext(context, mode); // sets stackMode!
yield* await service.executeCommandData(executeContext, commandData, progressState);
// Batch must be expanded before dispatch — nested replay is rejected loudly:
case 'Batch': return err(domainError.validation(
  { message: 'Batch undo/redo command must be expanded' }));
```

**Flow:** normal writes build BOTH directions up front (undo = restore old values/snapshot; redo = re-apply) via the typed append helpers, which normalize undefined→null cell values so JSON round-trips stay byte-stable → service stamps scope/createdAt/requestId and hands to the store → undo pops the undo side, executes it through the SAME command bus with a replay execution-context whose `stackMode='undo'` makes all nested writes self-suppress → redo mirrors from the other side. Snapshot-based appends filter to explicitly-targeted field ids only (storage/system fields captured incidentally must not replay).
**Invariant:** entries are DATA with a version number — old clients' entries are rejected by version, not misinterpreted; appends during replay are structurally impossible (mode gate), so undo of an undo converges; both commands must be non-empty or the entry is dropped (no dead stack slots); replay goes through the public command bus so permissions/side-effects/validation apply identically to fresh writes.
**Probe:** `packages/v2/core/src/application/services/UndoRedoStackService.spec.ts::"records update entries and skips when in undo/redo mode"` (:149), `::"executes undo/redo via command bus with context mode"` (:195), `::"normalizes undefined update values to null in stored undo commands"` (:117), `::"executes field type conversion replay via the command bus"` (:407).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "UndoRedoStackService appendEntry applyStackEntry UndoRedoStore",
  limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt command-replay undo for any collaborative editor surface: store forward+inverse COMMANDS with versions, gate appends by replay-mode/window presence, and route replay through the production bus. Adapt the supported-command set and version list to your write surface; pair with the DB-trigger capture capsule when raw SQL writes must also produce entries. Omit teable's window-scoped scope keying if single-session. Probes verified against the 800-line spec at HEAD.
