<!-- capsule-v2 -->
# Blank-text output ladder — when is a model response with no usable content a valid result vs a retry?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should an agent loop classify empty / blank-text / thinking-only responses?

## blank-text-output-ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:` `CallToolsNode` classification block (:1907–1935).
**Signature:** three booleans computed from `self.model_response.parts`: `is_empty`, `is_blank_text_only`, `is_thinking_only`.
**Data Shape:** parts vocabulary involved: `TextPart(content='')` preserved by adapters (gateway text items with `text: null` keep part IDs round-tripping), `ThinkingPart`.

### Decisive source
```python
is_empty = not self.model_response.parts
# A TextPart with empty content carries no text output; adapters preserve such parts
# (e.g. when a gateway returns a text item with `text: null`) so their IDs round-trip.
is_blank_text_only = not is_empty and all(
    isinstance(p, _messages.TextPart) and not p.content for p in self.model_response.parts)
is_thinking_only = (
    not is_empty and not is_blank_text_only
    and all(isinstance(p, _messages.ThinkingPart) or (isinstance(p, _messages.TextPart) and not p.content)
            for p in self.model_response.parts))
if is_empty or is_blank_text_only or is_thinking_only:
    # 1) token-limit exceeded → loud error, no retry
    # 2) content_filter (only on is_empty OR is_blank_text_only) → ContentFilterError w/ dumped body
    # 3) output_schema.allows_none → return None as a VALID result
    # 4) else fall through to schema-driven retry prompt
```

**Flow:** classify → token-limit gate fires first regardless of shape → content-filter check now ALSO catches blank-text responses carrying `finish_reason == 'content_filter'` (previously empty-only) → `output_schema.allows_none` treats any no-text shape as legitimate None → otherwise the retry prompt enumerates valid output kinds rather than assuming text exists.
**Invariant:** four rules:
1. Blank-text is DISTINCT from thinking-only AND from empty: adapters deliberately preserve zero-content TextParts for wire identity, so "empty" must mean NO PARTS, not falsy content.
2. Classification order matters: blank-text check precedes thinking-only, and thinking-only EXCLUDES blank-text-only (mutual exclusivity via the `not is_blank_text_only` clause).
3. Content filter applies to blank-text too — a provider signaling censorship through empty text items must surface as ContentFilterError, never as a retry loop.
4. The allows-none escape hatch exists because models legitimately emit only thinking after completing work via tool calls; forcing retries manufactures hallucinated follow-ups.
**Probe:** `tests/test_agent.py::test_agent_allows_none_output_blank_text_response` (:12343+, FunctionModel returning empty-content TextParts asserts success with None output).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "CallToolsNode is_thinking_only content_filter allows_none", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way classification + ordered gates for any agent loop deciding between accept/retry/error; adapt part types; omit the allows-none branch where outputs are non-optional.
