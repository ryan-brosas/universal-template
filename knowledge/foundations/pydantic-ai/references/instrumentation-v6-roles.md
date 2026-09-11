<!-- capsule-v2 -->
# Instrumentation v6 role grouping — how do you version an observability wire format without breaking old consumers?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does one new semantic-conventions role get introduced behind an opt-in version while old versions keep rendering identically?

## instrumentation-v6-roles
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/instrumented.py:` `_otel_message_role(part, version)` (:410–441), groupby keying in `InstrumentationSettings.messages` (:206–212), version literal widening `Literal[2..5]` → `[2..6]` (:72,:90,:158–162); docstring entry for version 6 (:129–135).
**Signature:** `key=functools.partial(_otel_message_role, version=self.version)` over each `ModelRequest.parts` — consecutive same-role parts merge into ONE ChatMessage.
**Data Shape:** returns `'system' | 'user' | 'assistant' | 'tool'`; v≥6 routes `BaseToolReturnPart` and `RetryPromptPart` WITH `tool_name is not None` to `'tool'`; earlier versions route them `'user'`. `SystemPromptPart | ToolAvailabilityDeltaPart` always `'system'`.

### Decisive source
```python
def _otel_message_role(part, version):
    if isinstance(part, SystemPromptPart | ToolAvailabilityDeltaPart):
        return 'system'
    elif version >= 6 and (isinstance(part, BaseToolReturnPart)
            or (isinstance(part, RetryPromptPart) and part.tool_name is not None)):
        return 'tool'
    else:
        return 'user'
```
Docstring rationale (load-bearing): ToolAvailabilityDeltaPart gets `system` "as the least-bad fit in a closed vocabulary... `tool` is the one role that would actively mislead, being paired with `tool_call_response`."

**Flow:** request parts stream through groupby keyed on role → a tool return followed by a user prompt splits into a `tool` message then a `user` one (v6) or ONE `user` message (≤v5) → consumers keying on message role see the convention-correct pairing of `tool_call_response` parts under `role='tool'` only when opted in.
**Invariant:** four rules:
1. Version-gating is INSIDE the per-part key function, not a separate renderer — old versions are bit-compatible by construction, and the default stays 5 until v3.
2. A RetryPromptPart counts as a tool response ONLY when it names a tool; a retry naming none renders as plain user content (matches what OpenAI adapters send).
3. Closed-vocabulary mapping needs an explicit least-bad assignment + written justification for non-obvious ones (delta→system), because silent defaults become folklore.
4. Version validation stays exhaustive-and-loud (`ValueError` listing legal values) with deprecation warnings on legacy versions 2–4.
**Probe:** `tests/models/test_instrumented.py` (grep hits for `version=6`/role assertions pin both renderings); `tests/test_vercel_ai.py` consumes the roles downstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_otel_message_role ChatMessage instrumented version tool role groupby", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt versioned-key-function grouping for any telemetry schema evolution; adapt roles/vocabulary; omit the legacy arms once your deprecation window closes (mirrors the transport deprecation pattern in tenacity-transport-replay).
