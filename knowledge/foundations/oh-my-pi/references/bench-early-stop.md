<!-- capsule-v2 -->
# Early-stop on verified match — aborting an agent run the moment its goal is verifiably reached

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** During a benchmarked agent run, how do you detect "the files already match the expected fixture" mid-run and abort cleanly — without corrupting the event collection, double-resolving promises, or failing when the abort surfaces inside `prompt()`?

## Serialized verification chain + settled-guard + abort-tolerant prompt
**Path/Symbol:** `packages/metaharness/adapters/edit/runner.ts` — `buildEarlyStop` (1038-1059), `collectPromptEvents` early-stop machinery (`triggerEarlyStop`, `earlyStopChain`, 1634-1656; abort-swallow at 1747-1755).
**Signature:** `buildEarlyStop(params): EarlyStopOptions | undefined` where `EarlyStopOptions = { check(): Promise<boolean>; onMatch(): void|Promise<void> }`; trigger condition: successful non-error MUTATION tool end.
**Data Shape:** check = fixture verification (`verifyExpectedFileSubset(expectedDir, cwd, files)`); state flags `earlyStopTriggered`/`settled` plus a serialized promise chain so concurrent triggers verify once.

### Decisive source
```ts
const triggerEarlyStop = () => {
    if (!earlyStop || earlyStopTriggered || settled) return;
    earlyStopChain = earlyStopChain.then(async () => {
        if (earlyStopTriggered || settled) return;
        let matched = false;
        try { matched = await earlyStop.check(); } catch { return; }
        if (!matched || earlyStopTriggered || settled) return;
        earlyStopTriggered = true;
        try { await earlyStop.onMatch(); } catch { /* swallow; still short-circuit */ }
        client.abort?.();
        resolveWait();
    }).catch(() => {});
};
...
try {
    await client.prompt(delivery.message);
} catch (err) {
    if (earlyStopTriggered) {
        // Abort raised inside prompt(); the run already short-circuited successfully.
        clearTimeout(timer); unsubscribe?.();
        return events;                       // success exit, not a throw
    }
    ...
    throw err;
}
```

**Flow:** every successful mutation-tool end schedules a check onto a SERIALIZED promise chain → the chain re-verifies flags after awaiting its turn (concurrent tool-ends cause one real verification) → run the fixture check; mismatch returns silently (run continues) → on match: mark triggered, log the `early_stop` event, abort the client, resolve the collector → if the abort escapes through `prompt()` as an exception, the caller RECOGNIZES it via `earlyStopTriggered` and treats the run as complete with the events gathered so far. Disabled by `earlyStopOnMatch === false` or zero target files.
**Invariant:** verification is serialized (never two concurrent checks racing the filesystem); once `settled`, nothing re-resolves or re-rejects (single-settle guard); an intentional abort is distinguished from a genuine prompt failure ONLY by the trigger flag — never swallow aborts unconditionally. The final verification still runs afterward; early-stop is an optimization that also freezes `success` evidence before further turns can mutate files.
**Probe:** exercised through the event-collector path in edit-benchmark runs; the deterministic pieces around it are pinned by `packages/metaharness/adapters/edit/runner.test.ts:63-108` (`summarizes completed runs…`, report-before-any-run) and the `earlyStopped` field flows into `TaskRunResult`. Coverage caveat: the race-free serialization itself is source-read; the surrounding result aggregation is test-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "buildEarlyStop triggerEarlyStop earlyStopChain verifyExpectedFileSubset abort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any agent loop with an externally checkable success predicate: serialize checks, single-settle, abort-and-treat-as-success, keep verifying after. Adapt the predicate (file match here; test suite, DB state elsewhere) and the trigger event to your domain; omit the hashline-specific logging shape. The abort-inside-prompt handling is the part porters get wrong — it is quoted in full above.
