<!-- capsule-v2 -->
# Line-clear animation choreography — delayed-done vs immediate-clear animation state machine

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How should transient status text exit the screen: instantly, animated, or held briefly so the user can read it?

## Two exit paths selected by target action
**Path/Symbol:** `src/ui/animations.ts:20-95` (`startLineClearAnimation`); selection logic `src/ui/renderer.ts:89-153`; constants `src/ui/types.ts:47-48` (`CLEAR_DELAY_MS = 15000`, `ANIMATION_STEP_MS = 500`).
**Signature:** `startLineClearAnimation(ctx, state, renderFn: RenderFn): void` hiding lines bottom-up via `state.hiddenFromBottomCount++`.
**Data Shape:** Completion action rebuilt from `storedAction` (steering keeps its reframeTier; inferring renders with empty outcome; done clears the widget entirely).

### Decisive source
```ts
  // Leaving analyzing to a non-done, non-analyzing action — animate the thinking
  // text away immediately (no delay), so it doesn't vanish instantly.
  // For 'done', use the delayed clear path instead so "✓ done" stays visible briefly.
  if (needsClearAnimation && leavingAnalyzing && !isDoneTransition) { ...startLineClearAnimation(...); return; }
  if (needsClearAnimation) {
    state.clearTimer = setTimeout(() => { ...startLineClearAnimation(ctx, state, boundRender); }, CLEAR_DELAY_MS);
```
Completion arm inside the animation (:63-86): no thinking lines or fully hidden ⇒ reset line state; done ⇒ null snapshot + REMOVE widget; inferring ⇒ render empty-outcome; else final render of completion action.

**Flow:** leaving analyzing → steering/watching/inferring ⇒ immediate bottom-up hide (500ms/line) → done ⇒ hold full thinking 15s THEN animate away then remove widget → any new updateUI cancels pending timers first.
**Invariant:** The 15s hold applies ONLY to done — steering feedback must be immediate or it desyncs from the steer message landing. Timer cancellation at every updateUI entry prevents overlapping animations (the "does not accumulate stale thinking through multiple rapid steers" test pins this). Animation operates on PLAIN mirrored lines while rendering re-styles them.
**Probe:** `grep -c "hiddenFromBottomCount++" src/ui/animations.ts` → 1. Direct tests: `tests/status-widget.test.ts:82/:108/:141/:174/:202/:231/:260/:293/:321/:344` (immediate-clear on steering, animation cycles for watching/inferring/waiting, rapid-steer staleness, "keeps thinking visible when leaving analyzing for done state", no-flash-on-reentry).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "startLineClearAnimation widget clear timer done", limit: 10 });
```

## Verdict
Adopt per-target-action exit choreography with timer preemption for any ephemeral status UI. Adapt delays to your UX (15s done-hold is a readability choice). Omit nothing on preemption — double-scheduled animations are the visible bug class this design exists to kill.
