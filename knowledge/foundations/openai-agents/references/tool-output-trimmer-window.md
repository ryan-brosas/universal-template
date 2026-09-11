<!-- capsule-v2 -->
# Tool-output trimmer window — how do you shrink old tool outputs under a char budget without mutating history or corrupting structured payloads?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** Where is the trim boundary, which outputs are eligible, and when does the trimmer refuse to touch a payload?

## Sliding-window input filter with fail-safe validation
**Path/Symbol:** `src/agents/extensions/tool_output_trimmer.py:` `ToolOutputTrimmer.__call__` (:136–202), `_find_recent_boundary` (:204–220), `_build_call_id_to_names` (:222–241), `_trim_function_call_output` (:243–270), `_trim_structured_function_call_output` (:272–336), `_structured_output_details` (:338–390), `_trim_json_schema` (:457–495).
**Signature:** `__call__(self, data: CallModelData[Any]) -> ModelInputData` (drops in as `RunConfig.call_model_input_filter`); config `{recent_turns=2, max_output_chars=500, preview_chars=200, trimmable_tools=None}`.
**Data Shape:** boundary = list index of the Nth-from-last `role=="user"` item; eligibility map call_id → (qualified, bare) tool names built from `function_call` items (`tool_search_output` maps to `("tool_search",)`).

### Decisive source
```python
boundary = self._find_recent_boundary(items)
if boundary == 0:
    return model_data                      # fewer than N user messages ⇒ nothing is old
...
if trimmable_tools is not None and not any(
        candidate in trimmable_tools for candidate in tool_names):
    new_items.append(item); continue
...
summary = (f"[Trimmed: {display_name} output — {output_len} chars → "
           f"{self.preview_chars} char preview]\n{preview}...")
if len(summary) >= output_len:
    return None, 0                         # never replace with something bigger
trimmed_item = dict(item)                  # copy, never mutate
trimmed_item["output"] = summary
```

**Flow:** locate boundary → build call_id→names → walk only `i < boundary` dicts → allowlist check (either qualified or bare name matches; None = all tools eligible) → string outputs over budget become preview summaries ONLY if strictly shorter → list outputs first pass through canonical-part validation (`_STRUCTURED_OUTPUT_FIELDS` allowlist, all-string values, known detail enums): anything non-canonical returns "no trim" — opaque payloads are never previewed — while valid ones get a header-fallback ladder (`[Trimmed: name; payload N…; dropped …]` → … → `[Trimmed]`) that always fits `max_output_chars` → `tool_search_output` results get recursive schema-prose stripping (drop description/title/$comment/examples; traverse only KNOWN structure keywords so user-controlled unknown keys survive).
**Invariant:** originals are never mutated (shallow item copies + a fresh ModelInputData); recent turns stay full fidelity; a replacement must be smaller than what it replaces; unknown data is preserved rather than guessed at.
**Probe:** `tests/extensions/test_tool_output_trimmer.py::TestRecentBoundary::test_custom_recent_turns` (:147), `::TestTrimming::test_does_not_mutate_original_items` (:959), `::test_canonical_structured_output_replays_through_chat_completions` (:434 round-trips trimmed canonical output back through the converter), `::test_custom_preview_chars` (:1011).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "tool_output_trimmer.py", fields: ["signature"], limit: 40 });
await mcp.codebase_memory.check_index_coverage({ project: "openai-agents-python", paths: ["src/agents/extensions/tool_output_trimmer.py", "tests/extensions/test_tool_output_trimmer.py"] });
```

## Verdict
Adopt user-message-anchored sliding windows and validate-before-preview for structured payloads; adopt smaller-than-original as an unconditional replacement gate. Adapt budget units (chars vs tokens) and your own summary header format. Omit schema-prose stripping unless you replay tool-search catalogs. Coverage: no_recorded_issue @ gen 2026-08-24T14:05:06Z.
