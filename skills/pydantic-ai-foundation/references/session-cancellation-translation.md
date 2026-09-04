<!-- capsule-v2 -->
# Session cancellation translation — how does an async cancel become a resumable domain exception?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you convert CancelledError into a typed cancellation carrying full resume state without swallowing real cancellations?

## session-cancellation-translation
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/agent/__init__.py:` setup-phase cancellation capture (:1311–1315), `_translate_cancellation` ctx mgr (:3369–3398), `_finalize_session_result` re-assertion (:3359–3361), bind/release wiring (:3395–3398); classic-run twin at :1764–1807.
**Signature:** `_translate_cancellation()` yields None; converts `exceptions.RunCancelled | asyncio.CancelledError`; `RunCancelled(message, messages=session.all_messages() or message_history, new_message_index=len(message_history), usage=run_context.usage, metadata=..., run_id=..., conversation_id=...)`.
**Data Shape:** `RunCancellation` controller with phases: `cancel_requested` flag → `bind()` (delivery arm once run has owning task) → `resolve()` (single consumer wins) → `release_issued()` (finally).

### Decisive source
```python
try:
    yield
except exceptions.RunCancelled as exc:
    # Match classic runs: a nested run carries its own history, but this session's
    # caller must receive the outer conversation it can actually resume.
    raise _run_cancelled('The agent run was cancelled by a nested run.') from exc
except asyncio.CancelledError as exc:
    cancelled = _run_cancelled('The agent run was cancelled.')
    if cancellation.resolve():          # we are the cancellation's single consumer
        raise cancelled from exc
    cancelled._attach_to(exc)           # not ours: ride along, don't swallow
    raise
finally:
    cancellation.release_issued()

# earlier, at result finalization:
if cancellation is not None and cancellation.cancel_requested:
    raise asyncio.CancelledError('pydantic-ai: re-asserting a requested run cancellation')
```

**Flow:** `RunContext.cancel()` during setup-phase hooks RECORDS instead of raising (:1311–1315 comment) → delivery waits for `bind()` after lifecycle entry → first await after binding ends the run → translator catches CancelledError → if OUR cancellation resolves, raise typed `RunCancelled` with complete resume state; if NOT ours (external task kill), attach info but RE-RAISE the original CancelledError.
**Invariant:** four rules:
1. Never convert a foreign CancelledError — `cancellation.resolve()` returning False means someone else cancelled this scope; `_attach_to` then re-raise preserves structured-concurrency semantics.
2. Resume state travels INSIDE the exception: full message history, new_message_index, usage, metadata, ids — so the caller can continue the conversation later.
3. Setup hooks are never interruptible: a request recorded pre-bind ends the run at the first await AFTER binding (#7386).
4. Re-assert at finalization: if cancel was requested but the run reached the end anyway, raise CancelledError rather than return a result the operator explicitly killed.
5. Nested-run RunCancelled is re-raised with the OUTER session's history ("the outer conversation it can actually resume"), not the nested run's.
**Probe:** `tests/test_agent.py` cancellation suites (session runs; grep `re-asserting a requested run cancellation` / `RunCancelled` in tests/test_agent.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "RunCancelled cancellation resolve release_issued bind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the resolve-or-reattach fork whenever translating cancellations into domain errors; adapt the payload fields to what YOUR resume needs; omit the nested-run branch if you have no nested-run concept.
