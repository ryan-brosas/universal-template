<!-- capsule-v2 -->
# Script-weighted token estimate — mixed-script char→token ratios without a tokenizer

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I estimate LLM token counts for budget checks when shipping a real tokenizer is too heavy — especially for CJK-heavy content?

## Division-by-ratio per script bucket, ceil, then safety buffer
**Path/Symbol:** `src/context/tokenEstimate.ts:estimateTokensByScript` (:76–94) + `countScripts` (:35–71) + `estimateTokensWithBuffer` (:96–102).
**Signature:** `countScripts(text): ScriptCharCounts`; `estimateTokensByScript(text): { tokens, counts }`; `estimateTokensWithBuffer(text, buffer = DEFAULT_SAFETY_BUFFER /* 0.15 */): number`.
**Data Shape:** `RATIOS = { latin: 4.0, cyrillic: 3.5, devanagari: 3.0, cjk: 0.6, other: 3.5 }` (chars per token); buckets counted via `\p{Script=...}` regexes; Han+Hiragana+Katakana+Hangul all fold into the single `cjk` bucket.

### Decisive source
```ts
const estimate =
  counts.latin / RATIOS.latin +
  counts.cyrillic / RATIOS.cyrillic +
  counts.devanagari / RATIOS.devanagari +
  counts.cjk / RATIOS.cjk +          // 0.6 chars/token ⇒ CJK ≈ 2–3 BPE tokens each
  counts.other / RATIOS.other;
return { tokens: Math.ceil(estimate), counts };
```

**Flow:** `Array.from(text)` codepoint iteration → classify each char into latin/cyrillic/devanagari/cjk → `other` is the RESIDUAL (`total − known`) so punctuation/emoji/digits are never dropped → weighted sum of divisions → ceil → optional ×1.15 buffer with its own ceil.
**Invariant:** The division direction IS the semantics: ratio = chars-per-token, so a small denominator inflates the estimate for token-dense scripts. Getting this backwards under-counts CJK by ~5×. Empty text returns `{ tokens: 0 }` without touching ratios.
**Probe:** No dedicated upstream test file exists for this module (verified: only re-export at `src/context/index.ts:6`). Coverage caveat recorded honestly; deterministic check pins `Math.ceil` and residual-`other` arithmetic against the source above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "estimateTokensByScript countScripts RATIOS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ratio table and division-by-ratio formula wholesale — it is runtime-agnostic and dependency-free. Adapt ratios if you target a specific tokenizer family (measure, don't guess). Omit the ScriptCharCounts exposure if your host needs only the scalar.
