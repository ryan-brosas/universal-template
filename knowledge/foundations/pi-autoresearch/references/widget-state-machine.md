<!-- capsule-v2 -->
# Widget state machine — why does the status widget stop showing transient states after the first result?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What is the exact precedence of widget states, and which width invariant keeps the TUI from crashing?

## createHarnessWidgetUpdater ladder — results dashboard > ready > hide; width = termWidth − 2
**Path/Symbol:** live copy `extensions/pi-autoresearch/index.ts:createHarnessWidgetUpdater` :154–340 (width fix :163–167); legacy twin `src/ui/widget.ts:20–263` (comment block :29–34, transient states :201–251, `clearSessionUi` :258–263).
**Signature:** `updateWidget(extCtx)`: no UI ⇒ return; `results.length > 0` ⇒ collapsed one-liner or expanded table (`dashboardExpanded` toggle); else name ⇒ 'ready'; else `setWidget('autoresearch', undefined)` (hide).
**Data Shape:** collapsed line: 🔬 N runs K kept [C💥] [F⚠] │ ★ metric: best #run (Δ%) │ conf: X× │ 🎯target ✓ / →target │ secondaries │ session name.

### Decisive source
```ts
// widget.ts:29-34 — the width comment IS the crash report
// Container wraps widgets with paddingX=1 (2 columns total), so the
// content width available to Text.render() is termWidth - 2. Using the
// unadjusted width for truncation produces lines wider than the Container's
// contentWidth, causing wrapTextWithAnsi to split incorrectly and the
// Container to double-pad, which crashes the TUI.
const width = termWidth - 2;
```

**Flow:** every state change → re-render current widget. Once ≥1 result exists the dashboard is the ONLY surface ("NEVER show transient states" — test-pinned as 'After first result: no transient states'); before that: running… → done/failed ('call log_experiment' hint) → ready → hidden. Best-run selection reverse-iterates kept rows within the CURRENT segment so later equal-value runs win display (stable tiebreak). Expanded header uses FULL termWidth for border dashes (cosmetic overflow accepted) while body lines use width−2.
**Invariant:** the −2 padding compensation is load-bearing — truncating at raw termWidth crashes the TUI via wrap/double-pad. Confidence coloring ladder (≥2 success / ≥1 warning / else error) is duplicated in three renderers (index.ts, widget.ts, table.ts) and MUST stay in sync when ported. Transient suppression prevents the widget flashing between iterations once real data exists.
**Probe:** direct tests `__tests__/unit/state.test.ts` describe('Widget state behaviors') incl. describe('Widget never flashes') :259–282 + describe('After first result: no transient states') :283–331; anchors `grep -c 'termWidth - 2' extensions/pi-autoresearch/index.ts extensions/pi-autoresearch/src/ui/widget.ts` → 3 + 3 = 6 lines (width fix + comment refs in both); `grep -rl confColor extensions/pi-autoresearch/index.ts extensions/pi-autoresearch/src/ui/widget.ts extensions/pi-autoresearch/src/dashboard/table.ts | wc -l` → 3 files (triplicated ladder).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "createHarnessWidgetUpdater dashboardExpanded setWidget termWidth", limit: 10 });
```

## Verdict
Adopt the state-precedence ladder and the width-minus-padding invariant verbatim; adapt glyphs/colors; consolidate the triplicated confidence ladder into ONE helper when porting (upstream duplication is a known hazard). Direct tests cover the state machine thoroughly.
