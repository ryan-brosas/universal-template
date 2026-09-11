<!-- capsule-v2 -->
# mode-transition exit attachments — how do you notify the model that a mode ended without double-notifying on quick toggles?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When leaving plan (or auto-accept) mode should inject an "exit" context attachment into the next turn, what state machine prevents both duplicate exits and lost exits during rapid Shift+Tab toggling?

## handlePlanModeTransition / handleAutoModeTransition: pending-flag latches with transition-edge clearing
**Path/Symbol:** `src/bootstrap/state.ts`:`needsPlanModeExitAttachment` (`:158-159`), `needsAutoModeExitAttachment` (`:160-161`), `handlePlanModeTransition` (`:1349-1363`), `handleAutoModeTransition` (`:1373-1399`), accessors (`:1341-1371`).
**Signature:** `handlePlanModeTransition(fromMode: string, toMode: string): void`; `handleAutoModeTransition(fromMode: string, toMode: string): void`; readers `needsPlanModeExitAttachment(): boolean`, `needsAutoModeExitAttachment(): boolean` — consumed-and-cleared by the attachment builder.
**Data Shape:** Two independent boolean pendings. Mode names are plain strings compared against `'plan'` / `'auto'`.

### Decisive source
```ts
// :1353-1362 — plan
// If switching TO plan mode, clear any pending exit attachment
// This prevents sending both plan_mode and plan_mode_exit when user toggles quickly
if (toMode === 'plan' && fromMode !== 'plan') {   // :1355
  STATE.needsPlanModeExitAttachment = false
}
// If switching out of plan mode, trigger the plan_mode_exit attachment
if (fromMode === 'plan' && toMode !== 'plan') {   // :1360
  STATE.needsPlanModeExitAttachment = true
}
// :1380-1384 — auto SKIPS the auto↔plan pair entirely
// Auto↔plan transitions are handled by prepareContextForPlanMode (auto may
// stay active through plan if opted in) and ExitPlanMode (restores mode).
// Skip both directions so this function only handles direct auto transitions.
if ((fromMode === 'auto' && toMode === 'plan') ||
    (fromMode === 'plan' && toMode === 'auto')) {
  return
}
```

**Flow:** every mode change routes through the handler → entering the mode CLEARS its pending exit flag → leaving it SETS the flag → next user-turn context build consumes the flag, attaches `*_mode_exit` content, clears it. Rapid toggle plan→normal→plan→normal within one turn yields ONE exit attachment, not two.
**Invariant:** The exit notification is a LEVEL-triggered latch (pending flag), not EDGE-emitted messages — so multiple transitions coalesce into at most one pending attachment per mode. Re-entering the mode cancels a pending exit (the "exit" would be stale). The auto variant deliberately ignores auto↔plan edges because those flows own their own attachment lifecycle elsewhere; double-handling would emit spurious exits for transitions that never left auto semantics.
**Probe:** Deterministic pins: `grep -n "toMode === 'plan'" src/bootstrap/state.ts` → `1355:`; `grep -n "fromMode === 'plan'" src/bootstrap/state.ts` → `1360:`; `grep -cn "fromMode === 'auto'" src/bootstrap/state.ts` → `2` (:1381 skip + :1386 local alias); `grep -n 'prevents sending both' src/bootstrap/state.ts` → `1354:` AND `1390:` (both handlers carry the rationale comment).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "mode transition exit attachment plan auto needsPlanModeExitAttachment", limit: 10 });
```

## Verdict
Adopt level-triggered exit latches with enter-clears/leave-sets edges whenever mode changes must inform the model exactly once. Adapt mode-name vocabulary and which transitions are exempt (your equivalent of the auto↔plan skip). Omit nothing else — the mechanism is four lines of state plus two pure functions.
