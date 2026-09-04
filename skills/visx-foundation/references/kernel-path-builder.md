<!-- capsule-v2 -->
# SVG path string builder — how do you emit precision-controlled path data (incl. full-circle arcs) without d3?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** Why does `rect` use relative commands, why do full circles need TWO arc segments, and what does the precision knob control?

## Fluent builder with toFixed rounding
**Path/Symbol:** `packages/visx-kernel/src/path/createPath.ts:createPath` (:130–132) + `PathBuilderImpl` (:28–128).
**Signature:** `createPath(precision = 3): PathBuilder` — fluent `moveTo/lineTo/quadraticCurveTo/bezierCurveTo/arc/rect/closePath()` returning `this`, `toString(): string`.
**Data Shape:** commands accumulate as strings joined with `''`; numbers pass through `Number(value.toFixed(precision)).toString()` (strips trailing zeros); points render as `x,y`.

### Decisive source
```ts
// rect via relative h/v — immune to accumulated rounding drift across corners
return this.append(
  `M${this.point(x, y)}h${this.number(width)}v${this.number(height)}h${this.number(-width)}Z`);

// SVG can't express a 360° arc in one command — split it
if (Math.abs(delta) >= TAU) {
  drawArc(startAngle, startAngle + delta / 2);
  drawArc(startAngle + delta / 2, startAngle + delta);
}
// first command auto-promotes to moveTo so arcs are chain-safe
if (this.commands.length === 0) this.moveTo(startX, startY);
else this.lineTo(startX, startY);
```

**Flow:** every append routes through the rounding `number()` → geometry helpers compute endpoints from angles → large-arc flag = `|to-from| > PI`; sweep flag encodes direction; counterclockwise normalizes delta into `[0,TAU)` with the `|| TAU` full-turn fallback.
**Invariant:** absolute-coordinate rects accumulate per-corner rounding error at low precision; relative `h/v` keep edges exact. Single-arc full circles silently render nothing in some renderers — the half-split is mandatory. Precision default 3 balances size vs fidelity for axis/bars.
**Probe:** `packages/visx-kernel/test/path.test.ts` (command strings incl. arc splitting).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "createPath precision drawArc", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whole file verbatim (~130 lines, zero deps); adapt precision default if your renderer differs; omit the TS interface if your host already types paths.
