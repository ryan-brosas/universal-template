<!-- capsule-v2 -->
# Retry ladder for benchmarked agent runs — timeout, no-op, and provider-failure retries that don't consume attempt slots

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you retry a benchmarked agent run on infrastructure failures (hangs, provider errors, read-only turns) so infra noise doesn't fail the task — while keeping those retries out of the task's real attempt budget and feeding the model actionable context?

## Three independent retry budgets + telemetry-carrying exceptions + followUp-as-retry
**Path/Symbol:** `packages/metaharness/adapters/edit/runner.ts` — `collectPromptEvents` (1565-1764, two-phase timer), `PromptTimeoutError`/`PromptTurnLimitError` with telemetry (436-465), `detectProviderFailure`+`AUTH_FAILURE_RE` (486-511), backoff `getProviderFailureRetryDelayMs` (513-516), retry-context builders (475-484, 518-530), the attempt loop in `runSingleTask` (1179-1405: `attempt--` at 1235/1284/1375).
**Signature:** `collectPromptEvents(client, delivery, config, logEvent, earlyStop?): Promise<Event[]>` — rejects with telemetry-carrying errors; `detectProviderFailure(events): { kind: "auth"|"provider"; message } | null`.
**Data Shape:** budgets default `{maxTimeoutRetries: 3, noOpRetryLimit: 2, maxProviderFailureRetries: 3}`; `PromptAttemptTelemetry = { elapsedMs, eventCount, toolExecutionStarts, toolExecutionEnds, messageEnds, lastEventType?, recentEventTypes[8], pendingRetry }`.

### Decisive source
```ts
// Start with the shorter connection timeout; upgrade to full timeout on first event
timer = setTimeout(fireTimeout, connectionTimeout);   // default 30s "no events at all"
...
if (!receivedFirstEvent) {
    receivedFirstEvent = true;
    clearTimeout(timer);
    timer = setTimeout(fireTimeout, config.timeout);  // full activity window
}
...
if (err instanceof PromptTimeoutError) {
    ...
    retryContext = buildTimeoutRetryContext(err.telemetry, timeoutRetriesUsed, maxTimeoutRetries);
    if (timeoutRetriesUsed >= maxTimeoutRetries) { /* Timeout exhausted → error */ break; }
    attempt--; // Don't consume a regular attempt slot for timeout retries
    continue;
}
// Provider failure only counts when NO mutation happened yet — an auth error
// after real edits is a different situation than a dead session.
if (providerFailure && !hasMutationToolCall) {
    const delayMs = getProviderFailureRetryDelayMs(providerFailureRetries); // 1s·2^(n-1), cap 10s
    await Bun.sleep(delayMs);
    attempt--; continue;
}
```

**Flow:** per attempt, build delivery (`prompt` initially, `followUp` carrying a retry-context message on later attempts) → collect events until `agent_end`, early-stop match, turn-limit breach, or timeout → classify outcome: timeout (with event telemetry in the thrown error) / zero-mutation-turn (read-only or no tools ⇒ nudge "you must use the edit tool") / provider-or-auth failure detected from assistant `errorMessage` fields (auth regex routes to a distinct category) / genuine verification result → each infra class has its own counter and cap; on retry, decrement the attempt index (infra retries are FREE), sleep the exponential backoff (provider only), and deliver the next prompt as a follow-up whose context names exactly what went wrong ("Previous attempt timed out waiting for agent_end after Xms. Observed events=…, last_event=…") → exhausted budget converts to a typed terminal error string that later marks the run as a transport failure (excluded from score denominators).
**Invariant:** infrastructure retries never consume the task's attempt slots and never count as benchmark failures until their own budget is exhausted; retry messages must carry concrete telemetry (counts, timings, last event type), not just "retry"; `agent_end` arriving during an auto-retry window is ignored (`pendingRetry` guard); the connection phase (no first event) gets its own shorter timeout than the activity phase.
**Probe:** behavior is exercised through `packages/metaharness/adapters/edit/runner.test.ts` result-shape tests (`retryStats` fields) and the summary pins `totalTimeoutRetries`/`totalZeroToolRetries`/`totalProviderFailureRetries` aggregation (runner.ts:1988-1993). No direct unit test drives the ladder itself end-to-end (requires live client fakes) — coverage caveat: the ladder's constants and guards are source-read; its aggregates are test-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "collectPromptEvents PromptTimeoutError detectProviderFailure retryContext pendingRetry agent_end", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape: independent per-class retry budgets, infra-retries-don't-consume-attempts via loop-index decrement, telemetry-stuffed retry context delivered as a follow-up, and the mutation-gate before counting a provider failure. Adapt timeouts/backoff caps and the auth regex to your providers; omit nothing structural. Caveat recorded honestly: aggregate counters are directly test-pinned; the ladder flow itself is source-grounded only.
