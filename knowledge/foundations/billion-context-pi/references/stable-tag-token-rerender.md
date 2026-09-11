<!-- capsule-v2 -->
# Tag token re-rendering — what token number may appear inside an injected `<acp tokens="...">` tag, and why not the calibrated one?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** Ref tags carry a human-readable size (`tokens="2.1K"`); when the model-facing array is rebuilt every turn, which value must that field hold so it never lies or churns?

## RAW-count stable tag rendering
**Path/Symbol:** `src/tag-tokens.ts`:3-15 whole file (15 lines: `formatTokens` :3-7, `stableTagTokens` :9-11, `rewriteTagTokens` :13-15); consumed at `src/messages.ts`:278, :313, :315 (both the kernel-body rebuild path AND the stable-append path); producer side documented in `src/system-prompt.ts`:9.
**Signature:** `formatTokens(tokens: number): string`; `stableTagTokens(text: string): string` = `formatTokens(defaultCountTokens(text))`; `rewriteTagTokens(tag: string, body: string): string` = `tag.replace(/tokens="[^"]*"/, \`tokens="${stableTagTokens(body)}"\`)`.
**Data Shape:** input tag = the matched `<acp ... mNNNNN</acp>` string; body = the text the tag will ride on (kernel core body after truncation, else original body). Output = same tag with ONLY the `tokens="..."` attribute rewritten. Ladder: <1000 → raw integer; 1000–9999 → one decimal + `K` (`2.5K`); ≥10000 → rounded integer + `K` (`12K`). No M tier here (unlike footer-status).

### Decisive source
```ts
// src/tag-tokens.ts:13-15 — the whole contract in one line:
export function rewriteTagTokens(tag: string, body: string): string {
  return tag.replace(/tokens="[^"]*"/, `tokens="${stableTagTokens(body)}"`);
}
// tests/tag-tokens.test.ts:83-93 — WHY raw and never density-calibrated:
test("tag tokens in output are raw-counted, not density-inflated", () => {
  ...
  assert.ok(text.includes(acpRef("m00001", "250")), `expected raw 250 tag, got: ...`);
  assert.ok(!text.includes('tokens="2.5K"'), "density-inflated tag value must not reach the model");
});
```

**Flow:** kernel emits CoreMessages whose first line carries a ref tag with a STALE/density-shaped `tokens=` value from decision-time arithmetic → on every rebuild (`coreOutToAgentMessages`), `patchRefTag`/`reconstructToolCallMessage` extract the tag, compute the body actually being sent, and call `rewriteTagTokens(tag, body)` → the model always sees a deterministic raw chars/4 count of exactly the bytes under the tag. Both paths use it: the truncated-rebuild path (:313) tags the KERNEL body, and the untouched-body path (:315) re-tags the ORIGINAL body — either way the value tracks the bytes the model receives, not any calibration state.
**Invariant:** (1) Tag values must be DENSITY-INDEPENDENT: two renders of the same message at different learned densities must be byte-identical (pinned by "deterministic across re-renders at different densities", tests/tag-tokens.test.ts:95-108) — otherwise context-cache keys and sequence alignment see phantom changes. (2) The value is computed from the body RIDDEN, not from stored metadata — after emergency truncation the tag shows the truncated size ("rebuild path ... tags the kernel body with raw tokens", :110-121). (3) `ref` (mNNNNN) and `type` attributes survive untouched — only `tokens=` is replaced. (4) The estimator inside is the SAME defaultCountTokens used for the raw estimate — but note the asymmetry vs decisions: decisions calibrate ×density, tags NEVER do. (5) Assistant messages get NO tag at all (messages.ts:302-305) — echo-prevention outranks annotation.
**Probe:** `cd $REFERENCE_ROOT/billion-context-pi && node_modules/.bin/tsx --test tests/tag-tokens.test.ts` → 7 pass / 0 fail executed GREEN at pin (covers format ladder boundaries incl. 999→"999"/10000→"10K", CJK counting, tool-result type preservation, truncation re-tagging).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "rewriteTagTokens stableTagTokens ref tag tokens", limit: 10 });
```

## Verdict
Adopt: any machine-injected size annotation shown to the model must be recomputed from the exact bytes it annotates, with a pure deterministic function of those bytes — never from cached/calibrated state. Adapt the format ladder and attribute grammar to your host's tag scheme. Omit nothing from the replace scope: replacing more than `tokens=` would corrupt refs (the compress address-space); replacing nothing leaves stale sizes after truncation.
