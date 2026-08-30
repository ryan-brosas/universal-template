<!-- capsule-v2 -->
# Turn-state machine — when should a protocol stream emit its request/response wrapper events, and who owns the transition?

**Source:** pydantic-ai Apache-2.0 `main@fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you derive protocol framing events (request start/end, response start/end) from an event flow that never mentions turns explicitly?

## _turn_to deduplicated transitions
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/ui/_event_stream.py:` `_turn` field (:119), `_turn_to` (:402–421); drivers: PartStartEvent→`'response'` (:239–241), ToolCallEvent→`'request'` (:257–258), AgentRunResultEvent→`None` (:263–264), error-path per-pending-call→`'request'` (:341–343), post-try→`None` (:373–374).
**Signature:** `async def _turn_to(self, to_turn: Literal['request', 'response'] | None) -> AsyncIterator[EventT]`.
**Data Shape:** `_turn: Literal['request', 'response'] | None`; hooks fired in order: close-old (`after_request`/`after_response`) → assign → open-new (`before_request`/`before_response`).

### Decisive source
```python
async def _turn_to(self, to_turn):
    if to_turn == self._turn:
        return                              # idempotent: same-turn is a no-op
    if self._turn == 'request':
        async for e in self.after_request(): yield e
    elif self._turn == 'response':
        async for e in self.after_response(): yield e
    self._turn = to_turn                    # assign BETWEEN close and open
    if to_turn == 'request':
        async for e in self.before_request(): yield e
    elif to_turn == 'response':
        async for e in self.before_response(): yield e
```

**Flow:** model starts streaming a part ⇒ response turn opens; a tool CALL arrives (model wants execution) ⇒ back to request turn; run result ⇒ turn ends (`None`). The error path re-enters `'request'` once per pending tool call before synthesizing its result part, so interrupted results land INSIDE a `<request>` block; the normal path exits to `None` only after the try block completes.
**Invariant:** three rules:
1. Transition events are emitted exactly once per actual change — repeated same-target calls are no-ops, so callers don't need to track current state.
2. Assignment happens between after-old and before-new: a hook reading `self._turn` during `before_request` already sees `'request'`.
3. Turn semantics follow EVENT meaning, not source ordering: a tool call mid-response-stream flips to request because the next thing that will happen (tool result) is client→server direction.
**Probe:** `.venv/bin/python -m pytest tests/test_ui.py -k 'run_stream_cancelled_run_closes_tools or test_run_stream_on_cancel' -p no:cacheprovider` (anchored at repo root; snapshots pin `<response>...</response><request><function-tool-result...>` wrapper placement around cleanup events).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_turn_to before_response after_request", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the derived-framing pattern (deduped state machine over semantically-meaningful events) for any protocol that wraps exchanges in envelope markers; adapt which events map to which turn; omit the error-path re-entry if your protocol has no per-request grouping.
