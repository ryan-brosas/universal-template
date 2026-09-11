<!-- capsule-v2 -->
# Helper trace wrapper + stream-tail telemetry capture — how do you instrument an agent-facing REPL without touching its helpers?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How does the CLI record per-step durations/errors and bounded output tails for telemetry while keeping helpers ignorant of observability?

## Post-import globals() wrapping
**Path/Symbol:** `src/browser_harness/run.py:_traced/_install_helper_trace/_StreamTail/main-capture` (:138-294).
**Signature:** `_traced(name, fn)` sets `wrapper.__bh_traced__ = True`; `_install_helper_trace()` mutates `run.globals()`; `_StreamTail(wrapped, limit)` wraps stdout/stderr remembering `(tail, length)`.
**Data Shape:** Trace entry `{helper, args[:300], duration_seconds, error[:300]?}` capped at 500 steps; exit payload includes stdout tail (20k), stderr tail (500), step_count, duration, exit_code, error_message.

### Decisive source
```python
def _install_helper_trace():
    from . import helpers
    g = globals()
    for name in dir(helpers):
        if name.startswith("_"):
            continue
        fn = g.get(name)
        if callable(fn) and not isinstance(fn, type) and not getattr(fn, "__bh_traced__", False):
            g[name] = _traced(name, fn)
```

**Flow:** main() resets counters → wraps streams in tails → `_run` executes user code → on SystemExit/Exception/completion captures ONE cli_event (action completed/error, command class from argv[0], self-reported browser kind, traced steps) → restores streams in `finally` → re-raises.
**Invariant:** Wrapping happens in the RUNNER'S namespace AFTER `from .helpers import *`, so helpers stay telemetry-blind and user code sees wrapped callables; `__bh_traced__` makes installation idempotent (double-wrap impossible); recorder.observe fires ONLY on success (errors carry their own entry); tails are pass-through so output still reaches the user; UTF-8 reconfigure at import guards cp1252/gbk Windows consoles (#124).
**Probe:** No direct unit test for the tracer (needs full CLI run) — coverage caveat; deterministic anchors verified in source: `__bh_traced__` (:170), finally-restore (:280-282), reconfigure (:8-11); adjacent `tests/unit/test_run.py` pins main()'s flow around it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "trace helper stream tail", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt runner-side wrapping + idempotence flags + bounded tails for any tool whose users are agents. Adapt event schema to your sink. Pair with the telemetry redaction capsule for privacy.
