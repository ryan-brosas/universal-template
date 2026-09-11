<!-- capsule-v2 -->
# Chart keyboard state machine — how do arrow keys traverse a chart's data points without ever focusing a hole?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** What is the minimal pure reducer that gives an SVG chart roving-tabindex point navigation with wrap-around, series jumps, and Enter/Exit memory?

## Two-mode reducer over seriesLengths
**Path/Symbol:** `packages/visx-a11y/src/keyboard/stateMachine.ts:transitionChartA11yKeyboardState` (:164–231); helpers `clampPoint` (:67–85), `movePoint` (:102–123), `moveSeries` (:125–150).
**Signature:** `transition(state: ChartA11yKeyboardState, seriesLengths: readonly number[], intent: ChartA11yKeyboardIntent): ChartA11yKeyboardState`.
**Data Shape:** `state = {mode:'chart'|'data', focusedPoint:{seriesIndex,index}|null, lastFocusedPoint}`; `seriesLengths` is a number[] (the ONLY geometry the reducer needs — ragged series are first-class); 10 intents.

### Decisive source
```ts
// wrap within a series — modulo arithmetic handles both directions
return { seriesIndex: focusedPoint.seriesIndex,
         index: (focusedPoint.index + direction + length) % length };

// moveSeries skips EMPTY series but keeps the column:
//   index: Math.min(focusedPoint.index, length - 1)

// exit preserves memory for re-entry
if (intent === 'exit') {
  return state.mode === 'chart' ? state
    : { mode: 'chart', focusedPoint: null,
        lastFocusedPoint: state.focusedPoint ?? state.lastFocusedPoint };
}
```

**Flow:** `enter` re-clamps `lastFocusedPoint` into data mode → arrows move points/series only while `mode==='data'` (early-return otherwise) → Home/End clamp inside the current series; Ctrl+Home/End jump to first/last NON-EMPTY point chart-wide → every write funnels through `setFocusedPoint`, which returns the SAME state object when nothing changed (`arePointsEqual`) so React bails out.
**Invariant:** navigation never lands on a nonexistent index: empty chart ⇒ reset to initial state; focus on an emptied series ⇒ `clampPoint` falls back to `getFirstPoint`. The focused-point identity test (`arePointsEqual` → return same ref) is what keeps re-renders free.
**Probe:** `packages/visx-a11y/test/keyboard.test.tsx :119/:157/:182/:214/:251` (Enter-driven flows incl. "wraps bar chart category focus with horizontal arrows" :147 and "wraps pie slice focus..." :165).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "transitionChartA11yKeyboardState", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "movePoint clampPoint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whole — the reducer is DOM-free and ports to any roving-tabindex widget; adapt intent→key mapping to your keymap; omit SVG-specific prop wiring. Full keyboard test suite pins the behavior.
