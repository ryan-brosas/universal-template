<!-- capsule-v2 -->
# Tool-call span discriminator — which spans count as tool calls across two instrumentation generations?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Given a span tree whose shape differs between instrumentation v2 and v3+, how do you identify real, executed tool-call attempts without counting output functions or deferred calls?

## attribute + name + msg three-signal classifier
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/agentic.py:_is_tool_call_span` (:105-136) with generation constants (:71-89); argument extraction `_extract_tool_call_info` (:146-158); ordering filter `_extract_tool_calls` (:165-169).
**Signature:** `_is_tool_call_span(node: SpanNode) -> bool`; `_extract_tool_calls(span_tree, *, include_failed: bool) -> list[_ToolCallInfo]`.
**Data Shape:** `_ToolCallInfo{name: str, arguments: str | None}` — arguments is the raw JSON string (v3 `gen_ai.tool.call.arguments` preferred, v2 `tool_arguments` fallback) or None when content capture was disabled.

### Decisive source
```python
tool_name = node.attributes.get('gen_ai.tool.name')
if not isinstance(tool_name, str): return False
if _TOOL_DEFERRAL_NAME_ATTR in node.attributes: return False   # 'pydantic_ai.tool.deferral.name'
if node.name == 'running output function': return False        # v2 output fn by NAME alone
if node.name == 'running tool': return True                    # v2 tool call
if not node.name.startswith('execute_tool '): return False     # v3+ prefix
msg = node.attributes.get('logfire.msg')
if isinstance(msg, str) and msg.startswith('running output function:'): return False
return True
```

**Flow:** iterate whole tree → keep spans passing the classifier AND (`include_failed` or `node.status != 'error'`) → sort by `start_timestamp` → project to `_ToolCallInfo`.
**Invariant:** Five exclusion/acceptance rules a porter will get wrong: (1) non-string `gen_ai.tool.name` ⇒ skip defensively (a malformed future span must not crash scoring); (2) deferral marker ⇒ never counted — an approved-later call did NOT execute in this run; (3) v2 output functions are excluded by SPAN NAME alone, independent of `logfire.msg`; (4) in v3+ both tools and output functions share the `execute_tool {name}` name, so the `logfire.msg` prefix `'running output function:'` is the ONLY discriminator; (5) every EXECUTION ATTEMPT produces a span — failures are filtered by status, not absence. Constants are deliberately duplicated from private `_instrumentation.InstrumentationNames` (in-source comment): pydantic-evals must survive spec evolution without a hard dependency.
**Probe:** `tests/evals/test_agentic_evaluators.py::test_tool_spans_v2_and_v3_both_detected_in_start_order` (:198-208), `test_tool_spans_ignore_output_function_spans` (:211-222), `test_tool_spans_ignore_deferred_tool_calls` (:225-240), `test_failed_attempts_excluded_by_default` (:243-258), `test_tool_spans_skip_non_string_tool_name` (:327-341).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"_is_tool_call_span","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `agentic.py 105-136`.

## Verdict
Adopt the classifier and its ordering guarantee verbatim for any OTel-span-based agent evaluation. Adapt constant values to your host's span vocabulary (keep them module-level and version-tolerant). Omit nothing — each branch corresponds to a pinned test. All five probes executed GREEN at pin (56-test suite).
