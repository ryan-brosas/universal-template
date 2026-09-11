<!-- capsule-v2 -->
# Event emission ordering — how do you make a 17-type streaming event vocabulary whose emission ORDER is itself the display contract?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A long multi-stage LLM run streams events to a terminal/notification consumer. Beyond "events arrive in some order", what ordering and content rules must hold so the stream renders correctly with zero client-side state, and where do raw internal ids get translated into display labels?

## DeepThinkEvent union + ordered emission in runDeepThink
**Path/Symbol:** `src/pipelines/deep-think.ts`: `DeepThinkEvent` union (:310-382, 17 types at :311), `makeToolEvent` filter (:965-973), solver_complete on done (:1104-1112), `judge_start` (:1247-1258), shuffle-note + ranked candidate summaries (:1337-1358), `judge_rankings`/`pairwise_summary` (:1366-1470), label-transformed `winnerRationales` (:1590-1618), `selected` (:1621-1641), solve `stage_complete` (:1643-1648).
**Signature:** `runDeepThink(prompt, options?): AsyncGenerator<DeepThinkEvent>`; every event is one object of the union pushed to one AsyncQueue — order of push == order of yield.
**Data Shape:** 17 types: `stage_start | stage_complete | candidate | selected | verified | complete | tool_start | error | ensemble_complete | solver_complete | verify_questions | verify_check_complete | revision_complete | checkpoint | judge_rankings | judge_start | pairwise_summary`; per-event optional fields are documented inline (e.g. `checkIndex`/`checkId` for verification, `judgeRankings` for multi, `pairwiseSummary` for pairwise).

### Decisive source
```ts
const makeToolEvent = (source: string, msg: Message): DeepThinkEvent | null => {
    if (msg.type !== 'tool_start' && msg.type !== 'tool_use') return null;
    return {
      type: 'tool_start',
      source,
      content: msg.toolName,
      toolInput: msg.toolInput,
    };
  };
```
```ts
        // Emit candidate summary events in ranked order
        for (let displayIdx = 0; displayIdx < judgeResult.indexMapping.length; displayIdx++) {
          const originalIdx = judgeResult.indexMapping[displayIdx];
          ...
          queue.push({
            type: 'candidate',
            stage: 'solve',
            content: `Candidate ${displayIdx + 1}: ${truncate(successfulCandidates[originalIdx], 200)}`,
            member: candidateMeta,
```
```ts
        queue.push({
          type: 'stage_complete',
          stage: 'solve',
          confidence: judgeResult.confidence,
          usage: combineUsage(usages),
        });
```

**Flow:** tool messages are filtered AT THE SOURCE (`makeToolEvent` passes only `tool_start`/`tool_use`, everything else becomes no event) → each solver done message yields exactly one `solver_complete` carrying that member's meta+usage → after the ensemble, `ensemble_complete` carries total usage → `judge_start` precedes judge execution and carries `judgeMode` + `judgeBackends` so the header can render before any result exists → a mode-specific shuffle NOTE is emitted as a `candidate` event before the summaries, then candidate summaries are emitted in RANKED display order (iterating `indexMapping`, not original order) with 200-char truncation → per-judge `judge_rankings` (multi) or `pairwise_summary` (pairwise) are emitted BEFORE `selected` so the reader sees the evidence before the verdict → `selected` carries `winnerRationales` with labels already transformed (`candidateId` → `#N <short-backend>`, `claude-code`→`claude`) so consumers never render raw ids in prose → the solve `stage_complete` is emitted AFTER judge selection (the solve phase is "complete" once a winner exists) and its `usage` is the CUMULATIVE `combineUsage(usages)` so far, not the stage's own delta.
**Invariant:** Emission order IS the contract: header-before-work (`judge_start`), evidence-before-verdict (`judge_rankings`/`pairwise_summary` before `selected`), note-before-list (shuffle note before candidate summaries); raw internal ids never reach prose fields — label transformation happens at emission time; tool-event filtering happens once at the source, not per consumer; cumulative usage on `stage_complete` means consumers can print running totals without summing.
**Probe:** the rendering side of this contract is pinned by `tests/commands/trace-format-e2e.test.ts` (236L whole file read pass 8) — EXECUTED pass 8: 9 pass / 0 fail (phase headers, `[solver-N:backend:model:module]` tool labels, truncation, completion status). The generator's own emission order has NO end-to-end test (standing caveat); source-pinned probe: `grep -n "queue.push" src/pipelines/deep-think.ts` shows the push sequence above.
**Coverage caveat:** the deliberate quirk — solve `stage_complete` after judge selection — will look like a bug to porters; it is load-bearing for the "one phase header per visible phase" rendering design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "DeepThinkEvent judge_start pairwise_summary selected stage_complete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the closed event union with inline-documented per-type fields, source-side tool filtering, header-before-work / evidence-before-verdict ordering, and emission-time label transformation. Adapt the type set to your stages. Omit the label transformation only if your ids are already human-readable.
