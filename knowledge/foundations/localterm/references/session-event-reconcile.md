<!-- capsule-v2 -->
# Session-event listener reconcile — when does an armed event listener need rebuilding?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you keep per-automation listeners in sync with edits without leaking timers or missing event-set changes?

## Signature-keyed stop-and-restart reconcile
**Path/Symbol:** `packages/server/src/session-event-manager.ts:SessionEventManager.sync` (:57–73) + `signatureOf` (:37–40).
**Signature:** `sync(automations: Automation[]): void` — idempotent, cheap, called after every automation mutation.
**Data Shape:** `entries: Map<id, { debounceTimer, signature, postRunGraceTimer, postRunGraceActive }>`; `signatureOf(automation)` = `` `${trigger.events.join(",")}:${automation.cwd}` `` for event automations, `""` otherwise.

### Decisive source
```ts
for (const [id, entry] of this.entries) {
      const automation = desired.get(id);
      if (!automation || signatureOf(automation) !== entry.signature) this.stopEntry(id);
    }
    for (const [id, automation] of desired) {
      if (!this.entries.has(id)) this.startEntry(automation);
    }
```

**Flow:** sync builds the desired set (enabled ∧ lifecycle "active" ∧ trigger.kind "event") → stops entries that vanished OR whose events/cwd signature changed → starts entries absent from the live map. Desired-set membership filters disabled/inactive/non-event; the signature comparison catches event-list or cwd EDITS on surviving automations.
**Invariant:** An edit to `trigger.events` must tear down and re-arm the entry — the armed debounce closure itself never consults the (possibly edited) trigger's event list at fire time beyond getAutomation re-read, so a stale entry would keep firing the OLD event set. The test pins exactly this: after switching events `[git-commit]→[cwd]`, git-commit no longer fires and cwd does.
**Probe:** `packages/server/tests/session-event-manager.test.ts` (`rebuilds the listener when the event set changes` :160–185, `tears the listener down once the automation leaves the desired set` :123).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "SessionEventManager sync signatureOf rebuild", limit: 10 });
```

## Verdict
Adopt the two-pass stop-then-start reconcile with content signatures (same shape as FolderWatchManager — one pattern, two managers); adapt signature fields to whatever config shapes your listener behavior. Directly tested.
