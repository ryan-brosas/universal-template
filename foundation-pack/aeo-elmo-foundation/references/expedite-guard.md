<!-- capsule-v2 -->
# Expedite guard — when may the healer drag a pending job forward?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How do you distinguish a genuinely stalled job from one that is merely between cycles — or deliberately backing off?

## The failure streak is the tell
**Path/Symbol:** `packages/lib/src/expedite.ts:shouldExpediteJob` (L20–44, whole file).
**Signature:** `shouldExpediteJob({ jobConsecutiveFailures, lastRunAt: Date | null, runFrequencyMs, now, minIntervalMs }): boolean`.
**Data Shape:** two refusals, no counters: `jobConsecutiveFailures > 0` → false; ran within `min(runFrequencyMs, minIntervalMs)` → false; else true.

### Decisive source
```ts
// A failed run records nothing, so "when did this last record a run?" cannot
// tell a healthy prompt from one whose provider is down — it says "never" for
// both … The failure streak on the job answers that, because a cycle writes
// it whatever the outcome.
if (jobConsecutiveFailures > 0) return false;
if (lastRunAt && now - lastRunAt.getTime() < Math.min(runFrequencyMs, minIntervalMs)) return false;
return true;
```

**Flow:** maintenance consults this only for prompts with an existing future (`created`) job. Pulling forward re-runs the whole paid fan-out, so false positives cost money. Nothing limits HOW OFTEN a prompt may be expedited because none is needed: a cycle either records a run (run-window then blocks) or fails (streak set) — either way the next pass refuses.
**Invariant:** "never-run" must never by itself authorize expediting a job that carries a streak; the streak travels on the job payload written by the previous cycle, so it is a decision record, not a guess.
**Probe:** `packages/lib/src/scheduling-under-failure.test.ts` describe "expediting still does its job" — stalled zero-streak job pulled forward; same job with streak=1 left alone.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "shouldExpediteJob jobConsecutiveFailures minIntervalMs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verbatim for any scheduled paid work with self-healing; adapt the min-interval constant (1h here); omit nothing — both guards are each the fix for a named incident class.
