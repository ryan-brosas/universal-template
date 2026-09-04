<!-- capsule-v2 -->
# RTL shadow mirror — how do directional shadows flip under RTL without regenerating tokens or styles?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter adding RTL support to a directional shadow/affordance system needs the swap-at-direction-layer pattern.

## Side-swap, not regeneration
**Path/Symbol:** `components/table/style/rtl.ts:genStyle` (7–52), importing `getShadowStyle` from `./fixed`.
**Signature:** identical tuple source: `const [leftShadowStyle, rightShadowStyle] = getShadowStyle(token);` then swapped application under `${componentCls}-wrapper-rtl`.
**Data Shape:** one file, 54 lines; re-uses the LTR primitive — zero duplicated color algebra.

### Decisive source
```ts
[`${componentCls}-cell-fix`]: {
  '&-start-shadow-show:after': rightShadowStyle,   // SWAPPED
  '&-end-shadow-show:after': leftShadowStyle,
},
[`${componentCls}-fix-start-shadow-show ${componentCls}-container:before`]: rightShadowStyle,
[`${componentCls}-fix-end-shadow-show ${componentCls}-container:after`]: leftShadowStyle,
```

**Flow:** the direction layer scopes everything under `-wrapper-rtl`, mirrors floats (`row-expand-icon`, `row-indent` → `float: 'right'`), rotates expand icons (`::after -90deg` open; collapsed `::before 180deg` / `::after 0deg`), and applies the SAME shadow class names emitted by the runtime but with left/right styles exchanged.
**Invariant:** the runtime emits identical class names in both directions; only the stylesheet decides which physical shadow answers a logical side. Tokens and shadow primitives stay untouched — directionality is purely an application-order concern. Consequence for porters: if you hard-code `left` inside your shadow generator, RTL must fork the whole primitive; keep primitives direction-free (logical properties + a final swap layer).

**Probe:** contrast read of `components/table/style/fixed.ts:60-61,89-90` vs `rtl.ts:37-38,48-49` — same selectors/classes, exchanged payloads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "wrapper-rtl direction rtl shadow expand icon rotate", limit: 10 });
```

## Verdict
Adopt "primitives are pure token functions; the direction layer remaps sides". Adapt float-based mirroring to logical CSS properties where your browser targets allow. Omit per-direction token variants — none exist here. Coverage: rtl.ts read in full (54 lines) plus fixed.ts cross-range; both `no_recorded_issue`.
