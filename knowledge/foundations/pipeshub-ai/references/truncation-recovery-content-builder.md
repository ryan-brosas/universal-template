<!-- capsule-v2 -->
# Truncation recovery (POST_MODEL content builder, loop-owned short-circuit)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/truncation_recovery.py` (whole file, 72L).

## Path/Symbol
- `default_truncation_recovery()` (:49) — closure counter `_CONSECUTIVE_TRUNCATION_THRESHOLD = 2`
- `_TOOL_CALL_TRUNCATION_NOTE` / `_TOOL_CALL_TRUNCATION_ESCALATED` (:20/:28)
- `_TEXT_ONLY_CONTINUATION_NOTE` (:40)
- Sets `ctx.recovery_tool_results: list[CoreToolResult]` or `ctx.recovery_message: UserMessage`

## Signature
POST_MODEL middleware; branches on `ctx.response.truncated` and on whether the truncated response carried tool_calls.

## Data Shape
Truncated WITH tool calls → one synthetic ERROR ToolResult per call (`is_error=True`, same tool_call_id/name) explaining the call was NOT executed. Truncated text-only → injected continuation UserMessage. >2 consecutive truncations → escalated directive (split work across smaller run_code calls; retrying identical output WILL truncate again).

## Decisive source
```python
# Pure content construction: whether to actually short-circuit the rest of
# the turn ... stays owned by the loop, since that is genuine turn-loop
# control flow, not a policy a middleware can express by itself.
```
(Header docstring — the middleware builds content; `Agent.run()`'s turn loop decides to skip execution and continue.)

## Flow
Non-truncated responses reset the consecutive counter to 0. Escalation threshold is strict-greater-than 2.

## Invariant
**Never execute tool calls parsed from incomplete arguments** — synthetic error results preserve the provider's pairing contract while blocking execution. The middleware/loop split is deliberate: content in middleware, control flow in the loop.

## Probe
No direct unit test found (grep over tests/ for `default_truncation_recovery`: zero hits) — coverage caveat recorded. Deterministic checks: error-shape ToolResults per call id; escalation only after >2 consecutive.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["default_truncation_recovery","recovery_tool_results","truncated"]'`

## Verdict
ADOPT. Completes this foundation's max-tokens story alongside synthesis-guard (input side): output-side truncation becomes structured feedback, never silent loss.
