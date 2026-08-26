<!-- capsule-v2 -->
# ifbench-turn-thread — how do you run a multi-turn capability benchmark as ONE cacheable conversation where the model's own reply IS the state?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How are turns chained, what makes the prompt prefix cacheable, and why does the first broken turn end the run?

## runner.ts turn engine
**Path/Symbol:** `packages/coding-agent/src/if-bench/runner.ts` (`runTarget`, `requestTurn`, `IfBenchTurnRecord`).
**Signature:** `runTarget(target: BenchTarget, options: IfBenchRunOptions): Promise<IfBenchModelReport>`; per-turn `makeActions(arrayLength, cumulativeActions, turn)`.
**Data Shape:** Report accumulates `turns[]`, `turnsPassed` (consecutive), `actionsPassed` (cumulative opcodes before first failure), cost/tokens; one shared `sessionId` feeds BOTH `apiKey` resolution and `promptCacheKey`; `temperature: 0`; owned `providerSessionState` map closed in `finally`.

### Decisive source
```ts
const expected = applyActions(state, actions);
...
if (!record.passed) {
	report.failure = { turn, kind: record.failure ?? "format", detail: record.response };
	break;
}
report.turnsPassed = turn;
report.actionsPassed = cumulativeActions;
state = expected;
// Replay the model's own reply as history: state lives in that text, and
// the provider payload keeps transport-native chaining intact.
if (outcome.message) messages.push(outcome.message);
```

**Flow:** Turn N issues N new opcodes onto an immutable prefix (system + all earlier turns byte-identical ⇒ provider prompt-cache reuse); later turns deliberately OMIT the array (`start` only on turn 1) so state lives ONLY inside the model's previous `<...>` reply — which is why drift is unrecoverable and the FIRST failed turn is the score. Provider errors become a distinct `provider` failure with `detail` = error text; empty text counts as a provider-class failure ("provider returned no text").
**Invariant:** Never rewrite or repair history mid-run — the accepted assistant message is appended verbatim; `maxTokens` is clamped to `model.maxTokens` when finite/positive; deterministic decoding (`temperature: 0`) keeps scores about capability, not sampling luck.
**Probe:** `grep -nF 'promptCacheKey: sessionId' packages/coding-agent/src/if-bench/runner.ts` → line `264` and `grep -cF 'providerSessionState' packages/coding-agent/src/if-bench/runner.ts` → `6`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "runIfBench IfBenchTurnRecord cumulativeActions modelFinished observer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt growing-conversation scoring with first-failure termination and reply-as-state; adapt credential/session plumbing; omit the observer hooks if headless. Direct test: `if-bench.test.ts` run suite ("carries state through the model's own replies…", thread-growth assertions 2 assistant / 3 user at turn 3, provider-failure classification).
