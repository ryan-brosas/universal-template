<!-- capsule-v2 -->
# Spring enter/exit trajectory — where do animated lines come from and go to, especially on inverted y-axes?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** What react-spring from/leave/enter config makes new lines fly in from a sensible edge and dying lines retreat, without flipping on SVG's inverted y?

## Trajectory table + SVG y-axis min/max swap
**Path/Symbol:** `packages/visx-react-spring/src/spring-configs/useLineTransitionConfig.ts:useLineTransitionConfig` (:60–101) + `animatedValue` (:17–35).
**Signature:** `useLineTransitionConfig({scale, animateXOrY: 'x'|'y', animationTrajectory?: 'center'|'min'|'max'|'outside'}) => {from, leave, enter, update}`.
**Data Shape:** scale.range() coerced to numbers; `fromLeave(line)` returns `{fromX,toX,fromY,toY,opacity:0}`; enter/update return real coordinates with `opacity: 1`.

### Decisive source
```ts
// correct direction for y-axis which is inverted due to svg coords
if (!shouldAnimateX && initAnimationTrajectory === 'min') animationTrajectory = 'max';
if (!shouldAnimateX && initAnimationTrajectory === 'max') animationTrajectory = 'min';

case 'outside':
default:
  return ((positionOnScale ?? 0) < scaleHalfwayPoint ? scaleMin : scaleMax) ?? 0;
```

**Flow:** compute range min/max (descending-safe via the shared `isDescending` swap), halfway point → pick per-line origin: `center` = middle of range; `min`/`max` = range edges; `outside` = NEAREST edge to the line's current position → entering lines animate from that value to their real position (opacity 0→1); leaving lines reverse it.
**Invariant:** the y-flip is NOT optional on SVG: 'min' means "bottom of the data" but SVG y grows downward, so the requested trajectory must swap for vertical animation or bars grow from the top. `outside` needs each line's own position (`from.x`/`from.y`), not the target's.
**Probe:** `packages/visx-react-spring/test/useLineTransitionConfig.test.tsx :7 invertedScale / :32 'min' / :45 expect(invertedResult.current.from(verticalLine).fromY).toBe(10)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useLineTransitionConfig animationTrajectory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt trajectory logic + flip rule verbatim; adapt spring configs (stiffness/damping live in AnimatedTicks etc., not here); omit visx axis/grid type glue.
