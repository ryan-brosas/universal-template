<!-- capsule-v2 -->
# Foveated renderer — how do you render a relevance field inside a hard token budget without lying about the remainder?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** A budgeted repo view must never exceed its token cap, must degrade gracefully at extreme budgets, and any "full list saved to…" footer must point at a file that actually holds the full list — what is the exact fit/disclosure/artifact contract?

## Heat-tier foveation + prefix binary-search budget fit
**Path/Symbol:** `src/core/render.ts:revealFoveated/revealGroups/tokenEstimate/directRelations` (:10-335); overflow key `src/core/ops.ts:overflowArtifact` (:608-609).
**Signature:** `revealFoveated(g, field: Float64Array, opts: RevealOptions): FitResult & { revealedIds, revealed }`; `tokenEstimate = ceil(len/4)`; tiers `HOT_TIER=0.3`, `WARM_TIER=0.02` (relative to field max), `MAX_UNRELATED_WARM_PER_FILE=4`.
**Data Shape:** Candidates = nodes above the glow floor (`h ≥ WARM_TIER*0.1`) minus `include`/`exclude`/already-`disclosed` ids (unless `repeatNucleus` re-admits seeds + direct relations). Sort: seeds > typed direct relations > contains-only/none, then heat desc. Output lines by tier: hot `▲ file:line sig [relation]`, warm one-liner, glow collapsed to per-file `~ +N more in <file>` counts.

### Decisive source
```ts
// Individual lines first, then glow; the prefix is over BOTH lists so the
// budget can shrink the periphery too; appending is byte-monotone → exact
// binary search, output can never exceed the budget.
const fits = (k: number): boolean => tokenEstimate(renderK(k)) <= opts.budget;
let k = items.length;
if (!fits(k)) {
  let lo = 0; let hi = items.length - 1; k = 0;
  while (lo <= hi) { const mid = (lo + hi) >> 1;
    if (fits(mid)) { k = mid; lo = mid + 1; } else { hi = mid - 1; } }
  if (!fits(0)) k = -1; // extreme budgets: header only
}
// The footer appears whenever anything was omitted — a collapsed glow
// periphery counts even when the rendered prefix fits — so the artifact
// write gates on the SAME condition, or the footer names a dead path.
const truncated = collapsed + individual - shown > 0;
```
```ts
// Disclosure is delta-based and id-stable:
if (opts.disclosed?.has(id) && !(opts.repeatNucleus && inNucleus)) { suppressed++; continue; }
...
return { ..., revealedIds: ids.slice(0, shown), revealed: revealed.slice(0, shown) };
// callers then: for (const id of fit.revealedIds) session.disclosed.add(id);
```

**Flow:** build candidate set (floor/scope/delta filters) → priority+heat sort → cap 400 → render hot→warm→glow with per-file warm caps → binary-search the largest fitting prefix over individual+glow lines → on truncation spill ALL rendered candidates (not just shown) to `overflowTo` tmp artifact named in the footer; unwritable artifact silently drops the footer note while keeping the budget.
**Invariant:** Budget is HARD (binary search on a byte-monotone render); `revealedIds` records ONLY nodes actually shown (≤ budget), which makes disclosure-set growth budget-bounded; the artifact always backs the "full list" claim (glow-collapsed nodes are written as real entries). Legacy-outline members keep `lineApproximate` and render "(member line unavailable)" instead of a false exact location.
**Probe:** `tests/render.test.ts` — 9× matrix "never exceeds budget (files×B)"; "keeps a structured focus nucleus while suppressing seen periphery" (second call suppresses, nucleus repeats); "collapses anonymous warm siblings instead of flooding one file" (4 + "~ +6 more"); "spills the full foveated list to a tmp file and names it in the footer"; "writes the artifact when only the glow periphery overflows".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "revealFoveated disclosed budget", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tier-by-relative-max rendering, the monotone-prefix binary search, delta disclosure via stable node ids with repeat-nucleus exemption, and the truncated⇔artifact coupling. Adapt tier constants and line formats to your domain. Omit the group variant's padEnd cosmetics.
