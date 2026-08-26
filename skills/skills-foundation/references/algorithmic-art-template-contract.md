<!-- capsule-v2 -->
# Algorithmic-art template contract — how do you make an LLM generate reproducible interactive artifacts without rebuilding the shell every time?

**Source:** anthropics/skills Apache-2.0 `main@3b3fad96af16`; Codebase Memory `skills`. **Question:** What is fixed vs variable in a generative-artifact template, and what makes output reproducible per seed?

## Seeded p5.js generator + fixed-shell viewer
**Path/Symbol:** `skills/algorithmic-art/templates/generator_template.js`:`initializeSeed` (:43–47), `regenerate` (:171–176), `exportImage` (:203–205); `skills/algorithmic-art/SKILL.md` STEP-0 (:105–127), REQUIRED-FEATURES (:259–272).
**Signature:** `function initializeSeed(seed) { randomSeed(seed); noiseSeed(seed); }`; `function regenerate() { initializeSeed(params.seed); }`.
**Data Shape:** single `params` object holds `seed` plus all tunables (counts/scales/probabilities/angles/palette array); export filename embeds the seed (`'generative-art-' + params.seed`); viewer sidebar = Seed section (display, prev/next, random, jump+Go) + Actions (Regenerate, Reset).

### Decisive source
```javascript
function initializeSeed(seed) {
    randomSeed(seed);
    noiseSeed(seed);
    // Now all random() and noise() calls will be deterministic
}
```
And the SKILL.md rule that makes the template a contract, not inspiration:
> **Use that file as the LITERAL STARTING POINT** - not just inspiration … **Keep all FIXED sections exactly as shown** (header, sidebar structure, Anthropic colors/fonts, seed controls, action buttons) … **Replace only the VARIABLE sections** marked in the file's comments.

**Flow:** setup() → initializeSeed(params.seed) → build entities (their constructors may call random()/noise(), already seeded) → draw() static (noLoop), animated, or redraw()-on-demand → parameter changes either update live or call regenerate() which RE-SEEDS before rebuilding → exportImage() writes a seed-stamped PNG.
**Invariant:** Reproducibility requires seeding BOTH generators — `randomSeed` alone leaves Perlin `noise()` flow non-deterministic — and any regenerate path must re-seed before reconstructing state. Same seed ALWAYS produces identical output.
**Probe:** repo-root deterministic probes (no upstream tests exist): `grep -n 'noiseSeed' skills/algorithmic-art/templates/generator_template.js skills/algorithmic-art/SKILL.md` — both files pin the dual-seed pair; `grep -c "params.colorPalette\[index % params.colorPalette" skills/algorithmic-art/templates/generator_template.js` = 1 (palette wraps modulo length).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", file_pattern: "*generator_template*", limit: 21 });
```
Live result 2026-08-26: 21 nodes incl. `initializeSeed` :43–47 (in=2), `regenerate` :171–176, `params` Variable :24–36, `Entity` Class :92–110.

## Verdict
Adopt the dual-seed invariant, params-object organization, seed-carrying exports, and the fixed-vs-variable split (shell/UX frozen, algorithm+parameter controls variable) for any LLM-authored artifact generator. Adapt branding (Anthropic fonts/colors are host-specific) and the p5.js choice. Omit the creative manifesto prompts (standing boundary). Caveat: markdown Section nodes in the graph carry heading ranges only; claims here rest on direct source reads of both files at the pinned commit.
