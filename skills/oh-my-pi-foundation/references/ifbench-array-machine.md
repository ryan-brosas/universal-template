<!-- capsule-v2 -->
# ifbench-array-machine — how do you build a reproducible working-memory benchmark whose ground truth never comes from the model?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How are the array, the per-turn opcodes, and their applications generated so turn N of any run is byte-identical and locally verifiable?

## actions.ts machine
**Path/Symbol:** `packages/coding-agent/src/if-bench/actions.ts` (`initialArray`, `makeActions`, `action`, `applyActions`, `encodeAction`).
**Signature:** `initialArray(length): string` (throws unless integer, even, in [8, 26]); `makeActions(length, start, count): Action[]`; `applyActions(input: string, actions: readonly Action[]): string`; `encodeAction(action): string`.
**Data Shape:** Ten action kinds; positions 1-based inclusive; kind chosen by `index % 10` (0 swap, 1 rotate-left, 2 reverse, 3 move, 4 rotate-right, 5 swap-pairs, 6 odd-even, 7 reverse-blocks size `(step%5)+3`, 8 rotate-span, default weave); opcodes are single glyphs (`⇄ ↶ ↷ ⌁ ↦ ⨯ ≺ ▥ ⤵ ⋈`) defined ONLY in the system prompt.

### Decisive source
```ts
let seed = 0x9e3779b9;
for (let i = chars.length - 1; i > 0; i -= 1) {
	seed = (Math.imul(seed, 1103515245) + 12345) >>> 0;
	const j = seed % (i + 1);
	[chars[i], chars[j]] = [chars[j]!, chars[i]!];
}
```

**Flow:** Start = `A..Z` truncated to even `length`, scrambled by a FIXED LCG (golden-ratio seed) — an alphabetical start would let a model reconstruct state from memory instead of reading its own previous reply. Every action is a pure function of its ABSOLUTE index (`step = index+1`), so turn boundaries are cosmetic: applying turns of 1+2+3 actions equals one run of 6 from index 0. `applyActions` folds all ten kinds as permutations; expected arrays are computed LOCALLY per turn (`expected = applyActions(state, actions)`), never trusted from the reply.
**Invariant:** Reproducibility — same `(length, start, count)` ⇒ identical tokens and result on every machine/run; no RNG beyond the fixed LCG; every kind is a permutation so characters are never lost.
**Probe:** `grep -nF '0x9e3779b9' packages/coding-agent/src/if-bench/actions.ts` → line `46`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "initialArray makeActions applyActions weave odd-even opcode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt absolute-index generation + local scoring + glyph opcodes; adapt the action set to your domain; omit the cat-sound contract (see ifbench-dual-contract). Direct test: `packages/coding-agent/test/if-bench.test.ts` ("permutes without losing characters…", "rejects array lengths the weave action cannot split" pinning `/even/` and `/\[8, 26\]/`).
