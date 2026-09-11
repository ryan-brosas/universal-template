<!-- capsule-v2 -->
# Progressive disclosure ops contract — what exactly does each of the four tools answer, and how does the session delta loop work?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** A model gets sketch/focus/dwell/impact — what is each tool's seed strategy and timescale, when is each legitimate, and how do repeat calls avoid re-paying tokens for known context?

## Four operators over one field + disclosed-set deltas
**Path/Symbol:** `src/core/ops.ts:sketch/focus/dwell` (:615-904); session keys `src/core/session.ts`; tool registration `src/index.ts:372-498`.
**Signature:** `sketch(root, budget?)` t=16; `focus(root, query, budget?, options?, ensured?)` t=FOCUS_T0=2; `dwell(root, factor?, budget?)` t←min(64, t·max(1.2, factor??2)); all return `OpResult {text, tokens, details}`.
**Data Shape:** Sketch seeds = production anchors (hubs whose closure reaches non-test files) + top-24 conductance hubs, capped 64. Focus resets `session.t/disclosed/focusKey/scope` on new focusKey or `fresh:true`. Dwell requires an existing focus ("no focus yet" guidance otherwise) and extends cached tk vectors when `chooseOrder(to)` exceeds the stored order.

### Decisive source
```ts
// Production anchors and hubs define the opening silhouette. Tests remain in
// the graph for focus/impact, but do not crowd out the code being shipped.
const productionAnchorIdx = anchorIdx.filter(i => closureFor(i).some(j => !isTestScope(nodes[j].file)));
...
groups.push({ label: "tests/fixtures", mass: testAnchorMass * 0.05,
  detail: `${testAnchorIdx.length} feature anchors collapsed` });
// Focus: fresh=true / new key → sharp restart; same query → nucleus repeats:
if (options.fresh || session.focusKey !== key) {
  session.t = FOCUS_T0; session.disclosed.clear(); ...
}
const fit = revealFoveated(g, field, { ..., disclosed: session.disclosed, seeds, repeatNucleus: true });
for (const id of fit.revealedIds) session.disclosed.add(id);
```

**Flow:** sketch surveys (anchors→basins→directories, tests discounted ×0.05/×0.1); focus centers (seed ladder → diffusion at t=2 → foveated reveal with suggested reads: merged 25-line windows around hot nodes, ≤5); dwell widens ONLY the delta (disclosure suppression returns newly relevant neighbors; header reports "context widened N×"); impact predicts review order. Tool descriptions carry usage discipline: dwell "use only when focus says more context remains"; overflow footers direct to the tmp artifact instead of huge budgets.
**Invariant:** The four tools are ONE operator at four timescales with ONE disclosure ledger per conversation-focus — repeated focus keeps its nucleus visible (`repeatNucleus`) while suppressing seen periphery ("N prior results omitted"), and any change of focus resets sharpness. Budgets clamp ≥256 regardless of caller.
**Probe:** `tests/ops.test.ts` — "repeats the active nucleus while suppressing previously seen periphery" ([focus] lines persist verbatim into call 2); "starts unrelated focuses sharp and never hides their target" (new query ⇒ t back to 2 even after dwell×8); "supports reproducible fresh focus and source scoping" (suppressed=0 under fresh+scope; suggestedReads deduped to one window per file); "dwell deepens the field and reports the t transition".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "sketch focus dwell productionAnchor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the operator decomposition (survey/center/widen/blast-radius), production-first discounting of test scope, the disclosure-ledger delta loop, and suggested-read windows as tool output. Adapt timescales to your graph sizes. Omit the TUI command surface (/fovea status|settings|reset|reload) as host product behavior.
