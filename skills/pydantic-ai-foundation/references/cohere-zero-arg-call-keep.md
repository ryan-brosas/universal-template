<!-- capsule-v2 -->
# Falsy-arguments tool-call drop — when may you truthiness-guard an optional field that can legitimately be empty?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (Cohere adapter); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A model emits a zero-argument tool call and the provider serializes `arguments` as `None` or `''` — why does a naive `if name and arguments` filter silently swallow the call, and what is the correct guard?

## cohere-zero-arg-call-keep
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/cohere.py:` `CohereModel._process_response` (:258–290, guard at :268).
**Signature:** `_process_response(self, response: V2ChatResponse) -> ModelResponse`; tool-call loop: `for c in response.message.tool_calls or []`.
**Data Shape:** Cohere v2 `ToolCallV2Function.arguments` for a zero-argument tool arrives as falsy (`None` or empty string) while `function` and `name` stay truthy; `ToolCallPart.args` carries the value verbatim.

### Decisive source
```python
# BEFORE #7720 (the bug):  if c.function and c.function.name and c.function.arguments:
# AFTER — presence checks only; arguments' VALUE never gates emission:
for c in response.message.tool_calls or []:
    if c.function and c.function.name:
        parts.append(
            ToolCallPart(
                tool_name=c.function.name,
                args=c.function.arguments,
                tool_call_id=c.id or _generate_tool_call_id(),
            )
        )
```

**Flow:** assistant message with ONLY a zero-arg tool call used to produce zero ToolCallParts → agent saw an empty response → "Please return text or call a tool." retry loop → budget exhaustion. Now the call survives with its falsy args preserved verbatim and the tool runs.
**Invariant:** three rules:
1. When mapping provider tool calls, gate on IDENTITY/presence fields only; an OPTIONAL PAYLOAD field whose legitimate domain includes empty values must never appear in the guard.
2. Preserve the empty payload verbatim on the mapped part — do not normalize `None`/`''` to `'{}'` here (downstream schema validation owns that decision).
3. The failure mode of getting this wrong is not a crash but a RETRY SPIRAL: the model's valid action vanishes from history, so it looks like disobedience. Audit every `and x.field` in adapter guards against the field's real domain.
**Probe:** `tests/models/test_cohere.py::test_zero_argument_tool_call[none]` + `[empty-string]` (:866+, parametrized; docstring pins the kept-with-falsy-value contract) and round-trip twin `test_zero_argument_tool_call_round_trip` (:915) — mock-client based; SKIPPED in repo `.venv` this pass solely for missing optional `cohere` package (import-time skip), source logic verified by direct read at :258–290.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "zero argument tool call CohereModel _process_response", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the presence-only guard rule for all provider adapters; adapt per-provider shapes (OpenAI-style adapters serialize `'{}'`, so their guards hide the bug); omit nothing. Pairs with test-model-generator-falsy-fixes (#7630/#7642) — same falsy-trap class on both sides of the wire.
