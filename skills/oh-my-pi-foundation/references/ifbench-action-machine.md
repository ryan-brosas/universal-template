<!-- capsule-v2 -->
# Character-array instruction machine — how do you build a fully reproducible, locally-scorable instruction-following task whose state lives only in the model's last reply?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How are actions generated from absolute indices so turn boundaries are cosmetic and expected results are computed host-side, never trusted from the model?

## Deterministic opcode stream
**Path/Symbol:** `packages/coding-agent/src/if-bench/actions.ts:` `initialArray` (:39–53), `makeActions`/`action` (:62–103, kind cycle at :68), `applyActions` (:106–166), `encodeAction` (:169–192); bounds `MIN_ARRAY_LENGTH = 8` (:15), even-length gate (:43–44).
**Signature:** `initialArray(length: number): string; makeActions(length, start, count): Action[]; applyActions(input, actions): string; encodeAction(action): string`.
**Data Shape:** Ten action kinds cycling every 10 absolute indices (swap/rotate-left/reverse/move/rotate-right/swap-pairs/odd-even/reverse-blocks/rotate-span/weave); glyphs (⇄ ↶ ↷ ⌁ ↦ ⨯ ≺ ▥ ⤵ ⋈) defined ONLY in the system prompt.

### Decisive source
```ts
let seed = 0x9e3779b9;
for (let i = chars.length - 1; i > 0; i -= 1) {          // fixed-LCG Fisher-Yates scramble
	seed = (Math.imul(seed, 1103515245) + 12345) >>> 0;
	const j = seed % (i + 1);
	[chars[i], chars[j]] = [chars[j]!, chars[i]!];
}
```

**Flow:** opening state = `A..Z[:length]` scrambled by a FIXED seed — "an alphabetical start lets a model reconstruct state from memory instead of reading its own previous answer" (:34–35) → turn N receives actions `[cumulative, cumulative+N)` (turn N issues exactly N opcodes) → model replies with the array inside `<...>` plus one cat sound → host computes `expected = applyActions(state, actions)` locally and compares. Every kind is a pure permutation, so character multisets are invariant.
**Invariant:** Reproducibility is index-based, not turn-based: "turn N of a run with array length L always issues the same tokens" — test-pinned as staged [1,2,3]-turn application ≡ one 6-action run from index 0. Even length is REQUIRED because weave splits in half (`throw … /even/`; bounds error names `[8, 26]`). Glyphs-without-glossary prevents natural-language paraphrase shortcuts. Executed verification at pin: `initialArray(8) === "BEDFAHCG"`, `initialArray(24) === "BFMNIAXVJCLQHOERPTDGSKUW"`; length-8 first three actions (⇄6,3 / ↶1 / ⌁2,4) transform `BEDFAHCG→BEHFADCG→EHFADCGB→EAFHDCGB`.
**Probe:** `packages/coding-agent/test/if-bench.test.ts` — `"permutes without losing characters and stays reproducible per absolute action index"` (:94, multiset + staging equality), `"rejects array lengths the weave action cannot split"` (:112, `/even/` and `/\[8, 26\]/`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "initialArray applyActions encodeAction", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: rank-1×3 exact — `initialArray actions.ts:39-53`, `applyActions :106-166`, `encodeAction :169-192`.

## Verdict
Adopt the absolute-index action generator + local scorer pattern for any capability benchmark that must be reproducible and ungameable by memory; adapt the permutation set to your domain. Keep glyph-opcode encoding only if your system prompt is the single glossary. Omit nothing behavioral — the fixed seed and even-length guard ARE the design.
