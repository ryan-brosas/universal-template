<!-- capsule-v2 -->
# Widget action state machine + line-clear animation — how does a live status widget transition without flashing stale thinking?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** Which transitions clear thinking immediately, which animate it away, and what guards prevent stale-content flash and timer leaks?

## updateUI + startLineClearAnimation (`src/ui/renderer.ts`, `src/ui/animations.ts`, `src/ui/types.ts`)
**Path/Symbol:** `renderer.ts:updateUI` (:19-176), `renderWithState` (:179-314); `animations.ts:startLineClearAnimation` (:20-95); constants `types.ts:46-48` (`WIDGET_ID='supervisor'`, `CLEAR_DELAY_MS=15000`, `ANIMATION_STEP_MS=500`).
**Signature:** `updateUI(ctx, state, supervisorState, action: WidgetAction)` — actions: watching | analyzing{thinking} | steering{message} | done | waiting{message} | inferring.
**Data Shape:** WidgetState carries `lastActiveState` (outcome+interventions snapshot), `lastThinking`, `lastThinkingLines` (PLAIN text mirror), `hiddenFromBottomCount`, `clearTimer`, `animationTimer`.

### Decisive source
```ts
// Every entry: kill BOTH timers first (no leak, no double animation)
if (state.clearTimer) { clearTimeout(state.clearTimer); state.clearTimer = null; }
// New thinking while analyzing ⇒ reset preserved lines (stale-flash guard):
if (hasNewThinking) { state.hiddenFromBottomCount = 0; state.lastThinkingLines = []; }
// leaving analyzing to non-done ⇒ immediate animate-away; done ⇒ DELAYED clear so
// "✓ done" stays visible CLEAR_DELAY_MS before animating:
const needsClearAnimation = (hasThinkingToAnimate && (!supervisorState?.active || leavingAnalyzing))
  || isDoneTransition;
// render: goal newlines collapsed to keep ONE header line; plainLines mirror kept for animation replays
widgetState.lastThinkingLines = plainLines;
```

**Flow:** analyzing streams judge reasoning live (thinking word-wrapped, ANSI-stripped width math via truncateToWidth on stripped lengths) → steering/watching clear thinking instantly → done renders "✓ done", waits 15s, then bottom-up line-hiding at 500ms/line until the widget is removed (`setWidget(WIDGET_ID, undefined)`). The plain-text line mirror lets animation re-render WITHOUT live thinking content.
**Invariant:** (1) Timer teardown precedes every decision — a fast watching→analyzing→steering burst can never stack animations. (2) `lastActiveState` is snapshotted BEFORE stop() on done (the code notes "supervisorState may already be inactive... capture state on that transition"). (3) Goal/thinking newline collapse keeps the header single-line (tested against real crash input "Fix two bugs\n1. Bug 2 (PRIMARY)"). (4) Width truncation uses STRIPPED-ANSI widths for arithmetic but themed strings for output.
**Probe:** `tests/status-widget.test.ts` — `clears old thoughts immediately when new thinking arrives` (:56), `immediately clears thinking when leaving analyzing for steering` (:82), `keeps thinking visible when leaving analyzing for done state` (:321), `sanitizes newlines in the goal` (:417), `truncates thinking lines to terminal width` (:487).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "updateUI startLineClearAnimation lastThinkingLines hiddenFromBottomCount", limit: 8 });
```

## Verdict
Adopt the six-action FSM + timer-first discipline + plain-line animation mirror for any TUI status surface. Adapt visual constants. Omit the 15s done-delay if your host removes widgets synchronously.
