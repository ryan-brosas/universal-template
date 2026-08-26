<!-- capsule-v2 -->
# Tool-results-first part sort — how do you keep provider-mandated part order while preserving system-prompt position?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When history rewriting must put tool results first, what else must not move?

## tool-results-first-sort
**Path/Symbol:** key fn `pydantic_ai_slim/pydantic_ai/messages.py::_tool_results_first_sort_key` (:2484–2490); consumers `_agent_graph.py:_merge_consecutive_messages` (:2932) and `models/__init__.py:_announce_tool_availability_delta_messages` (:2436–2438).
**Signature:** `key = lambda part: 0 if isinstance(part, ToolReturnPart | RetryPromptPart) else 1`; applied via STABLE `list.sort`, optionally over a sliced tail.
**Data Shape:** head/tail split sized by `_standing_system_prompt_count(request)` — only when the request is the history's FIRST kept request.

### Decisive source
```python
# models/__init__.py:
# Anthropic requires the tool results answering the previous turn to open the message,
# so the announcements sort to the back. One exception: system prompts opening the
# history's first request are the agent's standing prompt, which the adapters lift into
# the provider's dedicated system field based on exactly this position, so they stay at
# the front.
request = replace(message, parts=replacement_parts)
keep = _standing_system_prompt_count(request) if is_first_kept_request else 0
head, tail = replacement_parts[:keep], replacement_parts[keep:]
tail.sort(key=_tool_results_first_sort_key)
transformed.append(replace(request, parts=[*head, *tail]))
```

**Flow:** availability-delta announcements replace themselves in place (fixing an old bug where the fabricated ModelResponse jumped AHEAD of a user prompt sharing the request) → within the delta's own message, sibling parts are stable-sorted so tool results lead → standing system prompts on the opening request are exempted from sorting because adapters detect the system prompt BY POSITION.
**Invariant:** four rules:
1. Sort the TAIL only — hoisting logic keys on leading position, so a global sort would break system-field lifting on every provider that has one.
2. Stable sort preserves intra-class ordering (multiple results keep their relative order).
3. One shared key function everywhere: `_merge_consecutive_messages` was refactored from an inline lambda to this same symbol — drift between merge-order and announcement-order is how Bedrock turns get rejected ("Sort tool results ahead of tool availability announcements so Bedrock accepts turns revealing multiple tools", #7571).
4. The exempt head exists ONLY for the first kept request (`is_first_kept_request` flag resets after first delta-bearing request); mid-history system prompts are operator messages, not the standing prompt.
**Probe:** `tests/test_tool_availability_portability.py::test_announcements_render_after_sibling_tool_returns` (:1671) + `::test_standing_system_prompt_stays_ahead_of_sorted_tool_returns` (:1705); Bedrock acceptance `tests/models/test_bedrock.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_tool_results_first_sort_key announcements ToolAvailabilityDeltaPart standing system prompt sort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tail-scoped stable sorting whenever a wire format imposes partial order on mixed content; adapt the key predicate and the position-sensitive exemption; omit the exemption where your adapter has no positional system-lifting.
