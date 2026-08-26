<!-- capsule-v2 -->
# Shadow-mode rollout — observe, measure divergence, keep legacy authoritative

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you safely replace a security-critical component with a new implementation when you can't test it on production traffic directly?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/bashPermissions.ts` :1663-1739 — `CLAUDE_CODE_DISABLE_COMMAND_INJECTION_CHECK` env killswitch (:1678-1680), GrowthBook shadow flag `tengu_birch_trellis` gated behind inline `feature('TREE_SITTER_BASH_SHADOW')` (:1683-1685), single shared parse feeding both tiers (:1686-1695), shadow telemetry + forced legacy (:1701-1739).
**Signature:** shadow block runs the NEW parser, records one event, then sets `astResult = { kind: 'parse-unavailable' }` — legacy stays authoritative.
**Data Shape:** `tengu_tree_sitter_shadow { available, astTooComplex, astSemanticFail, subsDiffer, injectionCheckDisabled, killswitchOff, cmdOverLength }`.

### Decisive source
```ts
// Always force legacy — shadow mode is observational only.
astResult = { kind: 'parse-unavailable' }
astRoot = null
```

**Flow:** three independent switches: env killswitch (skip parse entirely), remote shadow flag (observe-only), and the bundle-time `feature()` gate kept INLINE in ternaries so Bun DCE strips the whole plane from builds lacking it. In shadow mode BOTH implementations run over ONE shared parse; the event captures four divergence axes (unavailability, too-complex verdicts, semantic failures, subcommand-split mismatches) plus the disable/killswitch/over-length context. Only after the telemetry proves parity does a later build flip TREE_SITTER_BASH to authoritative (the pure-TS parser's golden-corpus validation note documents the promotion).

**Invariant:** (1) Never let the new implementation decide while in shadow — force the old path AFTER recording. (2) Share the single parse between tiers so observation costs one parse, not two. (3) Every escape hatch (env killswitch, remote flag, build feature) stays independently operable; feature() must remain inline or DCE breaks and the code ships anyway. (4) Divergence telemetry should capture WHY-class (semantic fail vs split mismatch), not just a boolean.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'shadow mode is observational only' src/tools/BashTool/bashPermissions.ts` → :1736; `grep -nF 'GrowthBook killswitch for shadow mode' src/tools/BashTool/bashPermissions.ts` → :1681; graph resolves bashToolHasPermission :1663-2557 covering the block line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "bashToolHasPermission tengu_tree_sitter_shadow", limit: 5 });
```

## Verdict
Adopt the three-switch shadow harness for any security-component replacement; the one-event multi-axis divergence shape is the reusable telemetry contract.
