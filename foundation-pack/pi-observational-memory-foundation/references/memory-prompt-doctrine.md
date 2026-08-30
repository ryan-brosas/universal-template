<!-- capsule-v2 -->
# Memory-quality prompt doctrine — the three system prompts are a truthfulness contract, not style guides

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** What do the worker-agent system prompts actually enforce, so that porting them keeps the memories truthful instead of merely well-formatted?

## Prompt triad (`src/agents/{observer,reflector,dropper}/prompts.ts`)
**Path/Symbol:** `observer/prompts.ts:1` (`OBSERVER_SYSTEM`, ~119L), `reflector/prompts.ts:1` (`REFLECTOR_SYSTEM`, ~81L), `dropper/prompts.ts:1` (`DROPPER_SYSTEM`, ~48L).
**Signature:** plain exported template-literal constants injected as `AgentContext.systemPrompt`; no runtime templating, no few-shot examples beyond BAD/GOOD pairs.
**Data Shape:** every prompt opens with the same stakes frame — "These records are the ONLY information the assistant will have … Anything you distort here will be remembered wrong" — then a receive list, a procedure, emission rules, BAD/GOOD example pairs, and an explicit zero-output escape hatch ("it is fine to emit zero …").

### Decisive source
```ts
// observer/prompts.ts — the five load-bearing doctrines:
// 1. Assertions are authoritative; questions are not.
//   BAD:  User wondered if they have two kids.   GOOD: User stated they have two kids.
// 2. Frame state changes as supersession so the old state is explicit.
//   BAD:  User prefers React Query now.
//   GOOD: User will use React Query (switching from SWR).
// 3. Mark concrete completions explicitly ("completed:", "confirmed working")
//    so future runs know not to redo the work.
// 4. Split compound statements — one fact per observation enables
//    fact-granularity retrieval AND fact-granularity dropping downstream.
// 5. Relevance = resistance-to-drop, NOT priority:
//   "critical: … highest-resistance, load-bearing observations"
//   "Do NOT default to critical or high. Most observations are medium or low."
```
```ts
// reflector/prompts.ts — abstraction gate:
// "Over-reflection is also memory distortion: it makes transient details look
//  durable and crowds out the few facts future runs actually need."
// supportingObservationIds are "a coverage/provenance set and downstream dropper
//  coverage evidence … False or inflated support ids can cause unsafe downstream
//  dropper pruning." Coverage tiers are "review context … not a quota".
```
```ts
// dropper/prompts.ts — preservation floor:
// "Regardless of relevance label, budget pressure, coverage, or age, do not drop
//  observations that uniquely carry any of the following: user preferences …,
//  concrete completions …, named identifiers/file paths/SHAs, exact error messages,
//  architectural decisions and rationale, dates, unresolved blockers, non-standard
//  user terminology."
// "Maximum drops allowed this run … is a hard upper bound, not a target."
```

**Flow:** OBSERVER_SYSTEM ships to `runObserver` (chunk→observations), REFLECTOR_SYSTEM to `runReflector` (active pool→durable reflections), DROPPER_SYSTEM to `runDropper` (pool→safe drops); each ends its run by *not* calling the tool and emitting plain text.
**Invariant:** Prompt rules and code validators are SEMANTICALLY ALIGNED BY DESIGN — the prompt says invalid `sourceEntryIds` get rejected and the code rejects them atomically; the prompt forbids markdown/newlines/timestamps inside content and `isReflection`/`normalizeReflectionContent` enforce single-line at validation; the prompt tells the dropper coverage is evidence-not-quota while `selectDropCandidates` enforces the real ranking deterministically. Porting the prompt without the validator (or vice-versa) breaks the honesty model. Supersession framing exists specifically so the reflector cannot crystallize both old and new state as equally valid; assertion-over-question framing exists so a later question about a stated fact doesn't erase the answer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "OBSERVER_SYSTEM REFLECTOR_SYSTEM DROPPER_SYSTEM prompts", limit: 10 });
```
(Direct probe: `tests/observer.test.ts:42` "keeps core observer prompt rules" pins exact doctrine strings — `"Preserve user assertions exactly"`, `"Frame state changes as supersession"`, `"highest-resistance, load-bearing observations"` — and asserts absence of `"will NEVER be dropped"`/`"pruner"`. Prompts are otherwise prose: no direct unit test beyond this contract pin.)

## Verdict
Adopt the doctrine wholesale when porting any compress-my-history agent: assertions-authoritative, supersession framing, explicit completion markers, fact-granularity splitting, resistance-based relevance, abstraction gate, preservation floor, hard-bound-not-target budgets, and the zero-output escape hatch. Adapt domain examples (file paths, package managers) to your host. Omit pi-specific wording; keep the prompt↔validator semantic alignment — it is the actual invariant.
