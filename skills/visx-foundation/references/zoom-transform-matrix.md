<!-- capsule-v2 -->
# Zoom transform matrix — why does scale-around-a-point compose three matrices, and how does the ref beat stale wheel state?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** What is the exact math for zooming toward the cursor and why does Zoom keep a `matrixStateRef` alongside useState?

## T ∘ S ∘ T⁻¹ composition + ref mirroring
**Path/Symbol:** `packages/visx-zoom/src/Zoom.tsx:scale` (:166–186) + `matrixStateRef` (:117,141–150); algebra `util/matrix.ts` (`inverseMatrix` :32–49, `applyMatrixToPoint` :51–56, `multiplyMatrices` :77–88, `composeMatrices` :90–104).
**Signature:** `scale({scaleX, scaleY?, point?})`; `TransformMatrix = {scaleX,scaleY,translateX,translateY,skewX,skewY}`.
**Data Shape:** plain 6-field object (no arrays/classes) — cheap to spread, memo-key, or serialize via `toString()` → `` `matrix(a,b,c,d,e,f)` `` SVG string.

### Decisive source
```ts
// need to use ref value instead of state here because wheel listener
// does not have access to latest state
const translate = applyInverseMatrixToPoint(matrixStateRef.current, cleanPoint);
const nextMatrix = composeMatrices(
  matrixStateRef.current,
  translateMatrix( translate.x,  translate.y),
  scaleMatrix(scaleX, scaleY),
  translateMatrix(-translate.x, -translate.y),
);
```
```ts
// constraint hook: reject instead of clamp — returns PREV matrix on violation
if (shouldConstrainScaleX || shouldConstrainScaleY) return prevTransformMatrix;
```

**Flow:** inverse-map the focal point to pre-zoom coordinates → wrap a pure scale between two translations so the point stays fixed under the transform → constrain (default: scale bounds check returning prev; custom `constrain` prop fully replaces it) → setState AND mirror into `matrixStateRef`. Wheel handler scales around the cursor; pinch subtracts container rect from gesture origin (memoized across pinch frames); drag translates by start-point delta.
**Invariant:** (1) every mutation flows through `setTransformMatrix` — never set state directly — so constraint + ref mirror can't be bypassed; (2) zoom-around-origin without the T/–T sandwich jumps content to the origin; (3) constraint REJECTS rather than clamps, so repeated out-of-bounds wheels are no-ops (no value drift). Probe note: `return prevTransformMatrix;` also appears twice inside the JSDoc example block (:88/:91) — filter comment lines (`| grep -v '*'`) when counting executable sites (:134 is the only code site).
**Probe:** `packages/visx-zoom/test/Zoom.test.tsx :42-44` pins `inverseMatrix` export; interaction cases drive `toString()` output.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "Zoom matrixStateRef defaultConstrain", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "composeMatrices multiplyMatrices", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt matrix algebra file verbatim (pure math, zero deps) + the ref-mirror pattern for event-debounce staleness; adapt default 1.1/0.9 wheel factors; omit @use-gesture wiring if your host supplies events.
