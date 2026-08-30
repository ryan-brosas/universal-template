<!-- capsule-v2 -->
# Retry ladder & ParentCommand routing — What is retried, with what backoff, and how do Commands cross graph boundaries?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** Which exceptions are retry-eligible, how does backoff compute, and how does a node's Command reach the right graph level?

## Policy-match → attempts-only-failures → clamped exponential + jitter → RESUMING re-arm
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_retry.py:run_with_retry` (:573-682), `arun_with_retry` (:685-840), `_should_retry_on` (:841-856).
**Signature:** `run_with_retry(task, retry_policy, configurable=None) -> None`; `RetryPolicy(initial_interval=0.5, backoff_factor=2.0, max_interval=128.0, max_attempts=3, jitter=True, retry_on=default_retry_on)` (`types.py:418-438`).
**Data Shape:** Per-task override wins: `retry_policy = task.retry_policy or retry_policy`. `task.writes.clear()` before EVERY attempt so partial writes from failed attempts never commit.

### Decisive source
```python
except Exception as exc:
    if SUPPORTS_EXC_NOTES:
        exc.add_note(f"During task with name '{task.name}' and id '{task.id}'")
    if not retry_policy: raise
    matching_policy = None
    for policy in retry_policy:
        if _should_retry_on(policy, exc):
            matching_policy = policy; break
    if not matching_policy: raise
    attempts += 1                      # counts FAILED tries only
    if attempts >= matching_policy.max_attempts: raise
    interval = min(matching_policy.max_interval,
                   matching_policy.initial_interval *
                   (matching_policy.backoff_factor ** (attempts - 1)))
    sleep_time = (interval + random.uniform(0, 1)
                  if matching_policy.jitter else interval)
    time.sleep(sleep_time)
    config = patch_configurable(config, {CONFIG_KEY_RESUMING: True})
```
**Flow:** Exception ladder order matters: `ParentCommand` FIRST (routing below) → `GraphBubbleUp` (interrupt — end, no retry) → `asyncio.CancelledError` (see user-cancelled capsule) → generic `Exception` (policy match + backoff). ParentCommand routing: if `cmd.graph` matches this checkpoint ns (raw, recast, OR bare task name) the command executes HERE via the task's writers and the loop breaks normally; if `graph == Command.PARENT`, args are rewritten with `_checkpoint_ns_for_parent_command(ns)` and RE-RAISED to bubble to the parent graph. After each retry sleep, CONFIG_KEY_RESUMING=True tells subgraphs inside the next attempt to resume from their checkpoints rather than restart.

**Invariant:** max_attempts includes the first try ("Maximum number of attempts ... including the first"). Retry policies are matched per-exception by first-listed-wins across multiple policies. Sync nodes raising CancelledError convert to NodeCancelledError (LSD-1507) instead of silently looking like teardown.

**Probe:** `grep -n 'CONFIG_KEY_RESUMING: True' libs/langgraph/langgraph/pregel/_retry.py` → exactly 2 hits (:682 sync, :838 async); `grep -n 'NodeCancelledError(task.name)' libs/langgraph/langgraph/pregel/_retry.py | wc -l` → 2. Direct tests: `tests/test_retry.py:249 test_graph_with_single_retry_policy`, `:332 test_graph_with_jitter_retry_policy`, `:379 test_graph_with_multiple_retry_policies`, `:447 test_graph_with_max_attempts_exceeded`, `:159 test_checkpoint_ns_for_parent_command`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "run_with_retry", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exception-classification ladder ordering and writes-clear-per-attempt invariant verbatim. Adapt RetryPolicy defaults and Command routing grammar to your host's config keys. Omit the timed-attempt observer hooks (`CONFIG_KEY_TIMED_ATTEMPT_OBSERVER`, langgraph-server contract) unless you run a supervisor.
