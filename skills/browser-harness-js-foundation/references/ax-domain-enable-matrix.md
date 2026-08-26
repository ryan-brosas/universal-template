<!-- capsule-v2 -->
# ax-domain-enable-matrix — which Accessibility calls need `Accessibility.enable` and when do AXNodeIds stay stable?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** Which CDP Accessibility methods work without enabling the domain, and when must you enable it for stable node IDs?

## The enable/no-enable matrix
**Path/Symbol:** `skills/cdp/interaction-skills/accessibility-tree.md` "When to use each method" table (:90–99) + "`Accessibility.enable` — when you need it" (:101–111).
**Signature:** n/a — behavioral matrix over `Accessibility.{queryAXTree,getPartialAXTree,getChildAXNodes,getRootAXNode,getFullAXTree,getAXNodeAndAncestors}`.
**Data Shape:** NO enable needed: `queryAXTree` (one-shot semantic lookup by role/name), `getFullAXTree` (whole-page dump). ENABLE required: `getRootAXNode`, `getChildAXNodes`, other AX-walk methods; plus any multi-call flow that references nodes by AXNodeId across calls — without enable, node IDs can shift between queries.

### Decisive source
```md
You don't need `Accessibility.enable` for `queryAXTree` or `getFullAXTree`
(both work without it). You **do** need it for `getRootAXNode`,
`getChildAXNodes`, and the other AX-walk methods. The other reason to call
`Accessibility.enable` is to make **AXNodeIds stable across multiple calls**
(without it, node IDs can shift between queries).
```

**Flow:** targeted find → queryAXTree directly (no enable) → whole-page snapshot → getFullAXTree → multi-step walk referencing IDs across calls → enable first, disable after (enabling turns on page accessibility = runtime perf cost).
**Invariant:** The enable decision is orthogonal to the hang trap (see companion capsule): enabling does NOT fix the queryAXTree session-path hang. A porter who blanket-enables pays perf cost AND still hangs if routed through the wrong path.
**Probe:** `grep -cF 'stable across multiple calls' skills/cdp/interaction-skills/accessibility-tree.md` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "accessibility-tree" (Module node resolves line-exact).

## Verdict
Adopt the two-axis matrix (enable-for-walk-methods / enable-for-ID-stability) as portable CDP knowledge. Adapt role table to your app domain. Omit nothing else in this doc — it is already minimal.
