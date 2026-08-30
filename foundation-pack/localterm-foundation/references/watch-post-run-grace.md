<!-- capsule-v2 -->
# Post-run grace window — how do you stop a command's own side effects from re-triggering its automation?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** A watch-triggered run deletes the file it just processed — why doesn't that deletion fire the automation again?

## Finish-armed, resettable event-suppression latch
**Path/Symbol:** `packages/server/src/folder-watch-manager.ts:notifyRunFinished` (:161–175) + gate in `onFsEvent` (:138–140); identical mechanism in `session-event-manager.ts` (:92–103).
**Signature:** `notifyRunFinished(automationId: string): void`.
**Data Shape:** Per-entry `{ postRunGraceTimer, postRunGraceActive }`; grace duration = `AUTOMATION_WATCH_POST_RUN_GRACE_MS = 1_000` (constants.ts:716), shared by BOTH watch and event managers.

### Decisive source
```ts
if (entry.postRunGraceTimer !== null) clearTimeout(entry.postRunGraceTimer);
    entry.postRunGraceActive = true;
    entry.postRunGraceTimer = setTimeout(() => {
      entry.postRunGraceActive = false;
      entry.postRunGraceTimer = null;
    }, this.options.postRunGraceMs);
```

**Flow:** daemon's `onAutomationExit` hook calls notifyRunFinished for BOTH watch + event managers after updating run status → any fs/session event arriving while `postRunGraceActive` is dropped at EVENT TIME (before debounce arming) → timer expiry clears the flag. A second finish call clears + rearms, EXTENDING suppression.
**Invariant:** Three layers prevent self-retrigger loops and each is needed: (1) post-run grace drops the command's own side-effect events for 1s, (2) `isRunInFlight` drops events while the run is still launching/running, (3) fire-time re-read honors mid-debounce edits. Grace drops happen BEFORE debouncing — suppressed events don't even arm a timer.
**Probe:** `packages/server/tests/folder-watch-manager.test.ts` (`drops events during the post-run grace window` :239, `resets the grace window if notifyRunFinished is called again` :267); session twin `tests/session-event-manager.test.ts` :232/:254.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "notifyRunFinished postRunGrace", limit: 10 });
```

## Verdict
Adopt the finish-armed latch with drop-at-event-time semantics and the extend-on-second-finish behavior; adapt graceMs to your side-effect settling profile (deletes+editor churn settle fast; builds may need longer). Directly tested in both managers.
