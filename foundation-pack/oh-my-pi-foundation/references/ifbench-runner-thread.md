<!-- capsule-v2 -->
# Cacheable-prefix bench runner — how do you run a growing-conversation benchmark across models concurrently while keeping every thread's prompt prefix byte-identical for provider caching?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the turn engine's state-carry and termination contract, and which stream options make turns cacheable, deterministic, and chainable?

## One model = one growing thread
**Path/Symbol:** `packages/coding-agent/src/if-bench/runner.ts:` `runIfBench` (:116–139, worker pool :121–128), `runTarget` (:141–244), `requestTurn` (:246–299); session/state plumbing :157–176; first-failure break (:222–229); reply-as-history (:232–235).
**Signature:** `runIfBench(options: IfBenchRunOptions): Promise<IfBenchSummary>`; per-model `IfBenchModelReport {turnsPassed, actionsPassed, failure?, …}`.
**Data Shape:** Turn record `{turn, actions(=N), cumulativeActions, placement, durationMs, outputTokens, cost, passed, failure?, expected, response}`; failure `{turn, kind, detail}` with `turn: 0` reserved for preflight credential absence.

### Decisive source
```ts
const sessionId = options.randomSessionId();          // one id per thread
const apiKey = options.runtime.modelRegistry.resolver(model, sessionId);
...
const outcome = await requestTurn(model, context, sessionId, apiKey, providerSessionState, target, options);
...
state = expected;
// Replay the model's own reply as history: state lives in that text, and
// the provider payload keeps transport-native chaining intact.
if (outcome.message) messages.push(outcome.message);
```
Stream options (:261–274): `promptCacheKey: sessionId`, `maxTokens: min(flag, model.maxTokens)`, `temperature: 0` ("the benchmark measures capability, not sampling luck"), reasoning flags, shared `providerSessionState` map closed in `finally`.

**Flow:** fixed worker pool (`min(par, targets)`) pulls indexed queue slots; results land at their ORIGINAL index so output order is selector order regardless of completion order → per target: preflight credentials (fail fast as provider/turn-0 without burning turns) → loop turns: build prompt (start array on turn 1 only), compute expected locally, request, assess → pass ⇒ advance state to `expected`, push the model's OWN message back into history; fail ⇒ record first-broken turn and STOP ("state … cannot be recovered once it drifts") → summary counts failures.
**Invariant:** The system prompt + all earlier turns stay byte-identical across turns — that is what makes the whole prefix provider-cacheable under the stable `promptCacheKey`. Deterministic decoding is mandatory for comparability. Transport chaining survives via owned `providerSessionState` (per-provider entries torn down deterministically). Provider errors are a DISTINCT failure class from wrong answers (stream error events, stopReason error, empty text all map to `provider`). Concurrency is BETWEEN models only; one model's turns are strictly sequential.
**Probe:** `packages/coding-agent/test/if-bench.test.ts` — `"carries state through the model's own replies and scores the depth reached"` pins turnsPassed 2 / actionsPassed 3 / failure `{turn:3, kind:"cat"}` AND thread growth (turn-3 capture: 2 assistant + 3 user messages, no START reseed); `"classifies a provider failure separately…"` pins `{turn:1, kind:"provider"}`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "runIfBench providerSessionState promptCacheKey", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `runIfBench runner.ts:116-139` (+ Agent.promptCacheKey twin agent.ts:540-542 confirming the cache-key convention).

## Verdict
Adopt growing-thread scoring (depth reached = score, first broken turn terminates) for any cumulative-state capability benchmark; keep temperature 0 and stable cache keys or results aren't comparable. Adapt the provider plumbing; preserve index-ordered results under concurrency. Omit observer/board hooks if you report differently.
