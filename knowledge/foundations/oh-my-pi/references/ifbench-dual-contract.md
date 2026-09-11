<!-- capsule-v2 -->
# ifbench-dual-contract — how do you score working memory and instruction-following independently from ONE reply, including the echo-the-instruction loophole?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How does `assessResponse` separate "array right" from "sound present", and how does the matcher refuse both over-long sounds and the echoed directive text?

## protocol.ts scorer
**Path/Symbol:** `packages/coding-agent/src/if-bench/protocol.ts` (`catSoundPattern`, `assessResponse`, `RESULT_BLOCK`, `IfBenchFailure`).
**Signature:** `catSoundPattern(nyaMax: number): RegExp`; `assessResponse(response: string, expected: string, nyaMax: number): TurnAssessment`.
**Data Shape:** Failures `"result" | "cat" | "result+cat" | "format" | "provider"`; `TurnAssessment { passed, failure?, reported? }` where `reported` = block contents with cat sound + ALL whitespace stripped.

### Decisive source
```ts
return new RegExp(`nya{1,${nyaMax}}(?![a{])`);
...
if (!block?.[1]) return { passed: false, failure: "format" };
const reported = block[1].replace(cat, "").replace(/\s/g, "");
if (reported === expected) {
	return catPresent ? { passed: true, reported } : { passed: false, failure: "cat", reported };
}
return { passed: false, failure: catPresent ? "result" : "result+cat", reported };
```

**Flow:** One reply, two verdicts. The trailing lookahead `(?![a{])` kills TWO cheats at once: an over-long tail (`nyaaaaaaaaa` — the next char is another `a`) and the literal directive text `nya{1,8}` echoed back (next char is `{`). A missing `<...>` block is its own `format` failure; cat sounds INSIDE the block are stripped before comparison so `<ABCDEF nyaa>` still passes.
**Invariant:** The two contracts are scored independently — a model that nails the array but drops the sound fails (`"cat"`), one that echoes the instruction verbatim does NOT get credit for following it, and quoting inside the result block cannot smuggle the sound in because it is stripped before compare.
**Probe:** `grep -nF '(?![a{])' packages/coding-agent/src/if-bench/protocol.ts` → line `45`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "assessResponse catSoundPattern nya format failure assess", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-verdict taxonomy and the anti-echo lookahead; adapt the sound/directive pair to your own canary instruction; omit the glyph-opcode machine if you only need scoring. Direct test: `if-bench.test.ts` "refuses an over-long sound and the echoed directive itself" pins BOTH cheat forms.
