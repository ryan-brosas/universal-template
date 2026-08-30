<!-- capsule-v2 -->
# Widget action renderer — six-state status widget with width-aware truncation and thinking-line mirroring

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How does a footer widget render supervisor state changes without accumulating stale thinking text or overflowing terminal width?

## Action union drives everything
**Path/Symbol:** `src/ui/types.ts:7-13` (`WidgetAction` union), :30-43 (`createInitialState`); renderer `src/ui/renderer.ts:19-176` (`updateUI`), render body :179-314.
**Signature:** `updateUI(ctx, state, supervisorState, action = {type:'watching'}): void`.
**Data Shape:** Actions: `watching | analyzing{thinking} | steering{message} | done | waiting{message} | inferring`, each optionally `reframeTier`; widget line budget = `width - 1`.

### Decisive source
```ts
  // Always update last state first ... For 'done', supervisorState may already
  // be inactive (stopped before this call), so we also capture state on that transition.
  if (supervisorState?.active || action.type === 'done') {
    if (supervisorState) {
      state.lastActiveState = { outcome: supervisorState.outcome, interventions: [...supervisorState.interventions] };
    }
```
Goal-line width arithmetic (:243-255): prefix and suffix widths measured on ANSI-STRIPPED strings (`stripAnsi`), goal truncated via `truncateToWidth(rawGoal, availableForGoal)` where available subtracts prefix+suffix+closing-quote widths. Thinking words wrap into dim lines; plain mirrors stored in `lastThinkingLines` power later animation.

**Flow:** any state/action change → cancel pending clear/animation timers → capture snapshot when active-or-done → special inferring path (no goal yet) → needs-clear-animation? schedule :130-153 → inactive ⇒ remove widget (unless a clear animation is pending) → renderWithState builds the single header line + optional thinking lines.
**Invariant:** Snapshot-before-stop ordering is why 'done' can still display the outcome after `state.stop()` nulled it — a port that renders from live state only shows an empty widget on completion. ANSI-stripped measuring must match theme-colored rendering or lines overflow by the escape-sequence length.
**Probe:** `grep -c "CLEAR_DELAY_MS = 15000" src/ui/types.ts` → 1. Direct tests: `tests/status-widget.test.ts:416` describe('goal rendering'), `:435` describe('thinking multiline handling'), `:400` describe('widget visibility').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "startLineClearAnimation widget clear timer done", limit: 10 });
```

## Verdict
Adopt action-union-driven rendering with snapshot capture at transitions for any status surface driven by async state machines. Adapt the six actions and theme colors. Omit pi-tui specifics but keep stripped-width measurement if your renderer mixes styling with layout math.
