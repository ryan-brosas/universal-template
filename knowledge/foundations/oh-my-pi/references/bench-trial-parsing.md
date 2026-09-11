<!-- capsule-v2 -->
# Harbor trial parsing — reading pass/fail, reward, and spend out of native benchmark result files

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you parse a benchmark executor's per-trial directories and job-level result file into uniform trial rows — including running trials with no result yet — without misclassifying errors as failures?

## Dir-walk parsing + usage/reward fallback chains + exception-vs-reward precedence
**Path/Symbol:** `packages/metaharness/src/runner.ts` — `parseTrial` (638-733), `readTrials` (735-749), `readJobResult` (760-775), `resolveReward` (513-519), `aggregate` (794-830).
**Signature:** `function readTrials(jobDir: string): Trial[]`; `parseTrial(dir: string, name: string): Trial | null` (null = not a trial dir); `readJobResult(jobDir): JobInfo | null`.
**Data Shape:** trial dir = `<task>__<suffix>/result.json` (+ live `agent/omp.txt` transcript while running). Result fields: usage from `agent_result` else summed `step_results[].agent_result` (`cost_usd`, `n_input_tokens`, `n_output_tokens`, `n_cache_tokens`); reward from `verifier_result.rewards` else last step's; error from `exception_info.exception_type`; duration from ISO `started_at`/`finished_at`.

### Decisive source
```ts
// rewards: top-level verifier_result, else step_results last verifier
const collectRewards = (vr: unknown): void => {
    if (vr && typeof vr === "object") {
        const rw = (vr as Record<string, unknown>).rewards;
        if (rw && typeof rw === "object") rewards = rw as Record<string, number>;
    }
};
...
if (exc) { status = "error"; detail = exc.exception_type ?? "error"; }
else if (reward !== null && reward >= 1 - 1e-9) { status = "pass"; }
else { status = "fail"; }
```
```ts
// resolveReward: prefer the canonical `reward` key, else the max sub-reward
if (typeof rewards.reward === "number") return rewards.reward;
return Math.max(...vals);
```

**Flow:** walk job-dir subdirectories → missing `result.json` ⇒ RUNNING trial: duration from dir mtime, spend/tokens from the incremental cost probe of its live transcript → present `result.json` ⇒ drop the probe state and parse: sum usage across top-level + step agent_results; collect rewards preferring the top-level verifier then stepping through step_results; an `exception_info` object makes the trial ERROR (detail = exception type) regardless of any reward; otherwise pass iff `reward ≥ 1 − 1e-9` (epsilon compare), else FAIL → job-level totals come from the authoritative job `result.json` (`n_total_trials`, stats counts, terminal `finished_at`) with a disk-scan fallback in `aggregate`, where pending = total − done − running clamped at 0.
**Invariant:** exception beats reward (an errored trial is never scored); full reward 1.0 is compared with an epsilon, never `=== 1`; multi-reward verifiers resolve to the canonical key then max; running trials still report realtime spend rather than zero; authoritative job totals override per-trial arithmetic when present.
**Probe:** fixture-driven end-to-end via `packages/metaharness/test/manager.test.ts:44-117` — writes alpha (reward 1 + usage), beta (`exception_info` ⇒ error, detail `AgentTimeoutError`), gamma (no result ⇒ running), then asserts mirrored statuses/costs exactly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "parseTrial readTrials readJobResult resolveReward aggregate TrialStatus", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parsing contract for any executor-with-result-files integration: fallback chains over schema variants, epsilon reward comparison, exception-beats-reward precedence, live-probe spend for unfinished trials. Adapt field names to your executor's actual JSON; omit harbor specifics. Directly test-pinned through the REST layer with hand-written fixtures.
