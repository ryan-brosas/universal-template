<!-- capsule-v2 -->
# Two-contract turn scoring — how does one benchmark reply score two independent behaviors (working memory + instruction following) and name which broke?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the exact `assessResponse` verdict ladder, and how does the cat-sound matcher reject both over-long tails and echoed directive text?

## Failure taxonomy + anti-echo regex
**Path/Symbol:** `packages/coding-agent/src/if-bench/protocol.ts:` `IfBenchFailure` (:30), `DEFAULT_NYA_MAX = 8` (:33), `RESULT_BLOCK = /<([^>]*)>/` (:35), `catSoundPattern(nyaMax)` (:44–46), `buildTurnPrompt` (:65–89, placement wheel :71, middle split :75), `assessResponse` (:100–110).
**Signature:** `assessResponse(response: string, expected: string, nyaMax: number): TurnAssessment` where `TurnAssessment {passed, failure?, reported?}`.
**Data Shape:** failure ∈ `result | cat | result+cat | format | provider`; `reported` = block content with cat sounds + whitespace stripped; placement ∈ beginning/middle/end rotating by `(turn-1) % 3`.

### Decisive source
```ts
export function catSoundPattern(nyaMax: number): RegExp {
	return new RegExp(`nya{1,${nyaMax}}(?![a{])`);
}
...
const block = RESULT_BLOCK.exec(response);
if (!block?.[1]) return { passed: false, failure: "format" };
const reported = block[1].replace(cat, "").replace(/\s/g, "");
if (reported === expected) {
	return catPresent ? { passed: true, reported } : { passed: false, failure: "cat", reported };
}
return { passed: false, failure: catPresent ? "result" : "result+cat", reported };
```

**Flow:** reply → detect cat sound anywhere → extract first `<...>` block (missing ⇒ `format`, array unreadable even if a sound exists) → strip sounds/whitespace then compare to locally computed expected → four-way verdict names exactly which contract(s) failed. Prompt construction rotates the directive through beginning/middle/end so "a model cannot succeed by only attending to the prompt's edges"; the middle placement splits the action list in half AROUND the directive because an un-surrounded directive is unobservable. Only turn 1 carries `START <array>` — later turns deliberately omit it so state must be carried in the model's own previous reply.
**Invariant:** The trailing lookahead `(?![a{])` rejects TWO cheats at once: over-long runs (`nyaaaaaaaaa` > nyaMax fails because `a{1,N}` followed by another `a` is excluded) and literal directive echo (`nya{1,8}` quoted back — the `{` lookahead). Test-pinned: `<ABC DEF> nya` passes through whitespace/padding; `<ABCDEF nyaa>` passes with in-block sound stripped; exact-array-no-sound ⇒ `cat`; wrong-array-with-sound ⇒ `result`; both wrong ⇒ `result+cat`.
**Probe:** `packages/coding-agent/test/if-bench.test.ts` — `"separates the two contracts and reports which one broke"` (:126–131), `"refuses an over-long sound and the echoed directive itself"` (:133–136), `"rotates the cat directive through the prompt and only seeds the array once"` (:140–159).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "assessResponse catSoundPattern buildTurnPrompt", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: rank-1×3 exact — `assessResponse protocol.ts:100-110`, `catSoundPattern :44-46`, `buildTurnPrompt :65-89`.

## Verdict
Adopt dual-contract scoring whenever one artifact must satisfy independent requirements and triage matters more than a boolean; adapt the block grammar to your format. Keep the echo-rejection lookahead pattern for any "repeat token X" instruction test. Omit prompt templates (product wording).
