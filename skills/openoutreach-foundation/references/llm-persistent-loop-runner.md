<!-- capsule-v2 -->
# Persistent-loop sync runner — how do you call an async LLM SDK from sync code more than once without poisoning the thread or closing transports under GC?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** Why does every sync→async LLM call in this codebase go through one long-lived worker thread instead of `Agent.run_sync` or per-call `asyncio.run`, and what breaks otherwise?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/llm.py` — `_AgentRunner` (:45-68), `_get_runner` (:75-82), `run_agent_sync` (:85-87), `_MAX_RETRIES = 8` (:37-40).
**Signature:** `run_agent_sync(coro: Awaitable[_T]) -> _T`.
**Data Shape:** module-global `_runner: _AgentRunner | None` + `threading.Lock`; daemon thread named `"llm-runner"`; readiness via `threading.Event` so construction returns only after the loop is set.
**Graph evidence:** search_graph "split_model_id provider ladder credentials verify run_agent_sync" (19 total); trace inbound `run_agent_sync` = 17 callers across summaries, ml.qualifier, onboarding, discover, icp, qualify, top_up, and `verify_llm_credentials` — the single sync boundary for the whole funnel.

### Decisive source
```python
def run(self, coro: Awaitable[_T]) -> _T:
    """Submit *coro* to the runner loop; block until it completes."""
    return asyncio.run_coroutine_threadsafe(coro, self._loop).result()
```
Module docstring (:11-25) carries both regression rationales verbatim:
```python
# - `Agent.run_sync` uses an anyio portal that leaves the caller thread's
#   running-loop slot populated, poisoning later sync code on that thread ...
# - `asyncio.run` per call closes its loop on exit. The openai / anthropic
#   SDKs wrap `httpx.AsyncClient` in a subclass whose `__del__` does
#   `get_running_loop().create_task(self.aclose())`. If GC fires the
#   wrapper from call N during call N+1's loop ... →
#   `RuntimeError: Event loop is closed`.
```

**Flow:** first `run_agent_sync` call lazily constructs the runner (double-checked under lock) → dedicated daemon thread sets its own loop and `run_forever()` → every later coroutine is scheduled onto that same loop; all SDK HTTP clients therefore live on one loop forever and the caller thread's asyncio slot is never touched. Thread is a daemon: no shutdown path needed.
**Invariant:** Never create or close a loop on the caller's thread; never let a client outlive its loop (the GC-timing bug is eliminated by co-location, not by disabling GC). Retry policy rides the SDK: `_MAX_RETRIES = 8` overrides the default 2 because each retry honors `Retry-After` with jittered exponential backoff — ~1–2 minutes of 429/529 capacity blips ride through instead of failing in ~1.5s.
**Probe:** `tests/test_llm.py` whole (71 L) — no direct test drives the runner itself (its consumers do); the file pins the factory/verify layer above it (`test_verify_llm_credentials_*`). Caveat recorded: runner concurrency behavior is exercised only indirectly.
**Coverage:** `check_index_coverage` openoutreach/core/llm.py + tests/test_llm.py → no_recorded_issue / metadata_match.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "run_agent_sync persistent event loop runner", limit: 10 });
```

## Verdict
Adopt: one lazily-built daemon-thread loop as the sole sync→LLM boundary, with the two failure rationales written where the next porter will read them; SDK-level retry count raised rather than hand-rolled retry loops. Adapt thread naming/readiness to your runtime; omit the specific pydantic-ai portal critique if your stack differs — but re-derive why per-call `asyncio.run` is unsafe before dropping the pattern.
