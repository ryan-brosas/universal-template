<!-- capsule-v2 -->
# Handoff history parser tail — how does a nested summary survive repeated handoffs without losing empty turns or fabricating prose?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When a prior summary message is re-flattened on the next handoff, how do you split numbered records that may span multiple lines, parse JSON vs `role: content` records, recover separator-less bare-role records from older summaries, and reject prose instead of turning it into a fabricated message?

## Numbered-record splitting + JSON/legacy/bare-role parse ladder + writer pairing
**Path/Symbol:** `src/agents/handoffs/history.py:` `_flatten_nested_history_messages` (:456–467), `_extract_nested_history_transcript` (:469–491), `_split_summary_records` (:494–520), `_starts_numbered_summary_record` (:523–525), `_parse_summary_line` (:529–570), `_strip_summary_line_number` (:573–577), `_parse_summary_json_item` (:580–588), `_parse_legacy_typed_item` (:591–602), `_strip_transcript_item_metadata` (:605–609), `_KNOWN_TRANSCRIPT_ROLES` (:612), `_is_bare_role_record` (:615–620), `_split_role_and_name` (:623–630); writer side `_build_summary_message` (:376–398), `_format_transcript_item` (:401–412), `_format_transcript_item_json` (:415–421), `_format_transcript_item_legacy` (:424–443).
**Signature:** `_extract_nested_history_transcript(item) -> list[TResponseInputItem] | None`; `_parse_summary_line(line) -> TResponseInputItem | None`; `_build_summary_message(transcript) -> assistant message dict`.
**Data Shape:** input = one assistant message whose string content is `preamble\n<start marker>\nN. record\n…\n<end marker>`; output = re-parsed items (messages with explicit `content`, typed items with re-stamped `type`); preamble must be in `_SUPPORTED_CONVERSATION_HISTORY_PREAMBLES` (current + legacy strings); markers overridable via `set_conversation_history_wrappers`.

### Decisive source
```python
# _split_summary_records: a NUMBERED record may span multiple physical lines
if starts_numbered_record or not current_is_numbered:
    records.append("\n".join(current))
    current = [raw_line.strip()]
    current_is_numbered = starts_numbered_record
    continue
current.append(raw_line.rstrip())   # unnumbered line folds into the open numbered record

# _parse_summary_line: JSON first, then role:content, then bare-role recovery only
parsed_json = _parse_summary_json_item(stripped)
if parsed_json is not None:
    return parsed_json
role_part, sep, remainder = stripped.partition(":")
if not sep:
    if not _is_bare_role_record(stripped):
        return None                  # prose is rejected, never fabricated
    ...
    recovered["content"] = ""        # explicit empty content keeps it replayable
    return cast(TResponseInputItem, recovered)
...
reconstructed["content"] = content   # set even when empty
```

**Flow:** flatten pass walks items; an assistant message whose first line is a supported preamble AND whose remainder starts/ends with the wrapper markers is extracted → body split into records where unnumbered continuation lines attach to the preceding numbered record (so multi-line JSON records stay intact) while unnumbered lines after an unnumbered record start new records → each record: strip `N.` prefix, try `json.loads` (JSON-formatted records; `provider_data` popped, SDK-internal metadata stripped), else partition on first `:` — message roles (`user/assistant/system/developer`) become `{role, name?, content}` with content set even when empty; non-message roles route to `_parse_legacy_typed_item` which parses the JSON payload, pops `provider_data`, and re-stamps `type`; a colon-less line is recovered ONLY when it is a lone known role token optionally `(name)`-suffixed (bare-role recovery for pre-separator summaries) → anything else returns None and is dropped. Writer pairing: `_format_transcript_item` always emits `role: content` (separator present even for empty content) and switches to single-line JSON when content contains newlines or is non-string — so every turn the writer emits is one the parser can recover.
**Invariant:** round-trip stability across N handoffs — no turn is lost (empty turns keep explicit `content=""` because adapters like the ChatCompletions converter only recognize a message when both role and content keys exist) and no turn is invented (prose inside the block is dropped, not parsed); `provider_data` and SDK-internal metadata never survive a flatten.
**Probe:** `tests/test_handoff_history_duplication.py::test_bare_role_record_from_an_older_summary_is_recovered` (:2301 — `2. assistant` recovers to `{"role": "assistant", "content": ""}`), `::test_prose_inside_the_summary_block_is_still_rejected` (:2325 — numbered stray prose dropped, 2 of 3 records survive), `::test_recovered_empty_turn_keeps_explicit_content` (:2357 — both bare role and `assistant: ` yield `{"role": "assistant", "content": ""}`), `::test_nested_history_survives_repeated_handoffs` (:2279 — 3 nest hops keep all 3 turns), `::test_second_pass_nesting_keeps_empty_turns_provider_valid` (:2387 — flattened transcript converts through `Converter.items_to_messages`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "history.py", query: "parse summary line bare role", limit: 20 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.handoffs.history._parse_summary_line" });
```

## Verdict
Adopt the numbered-record transcript encoding with multi-line record grouping, JSON-first/legacy-second/bare-role-last parse ladder, fail-closed prose rejection, and explicit-empty-content recovery for any lossy context-transfer format that must survive repeated re-encoding. Adapt marker strings, preamble set, and known-role vocabulary. Omit bare-role recovery if your writer always emitted separators (it exists only for pre-separator legacy summaries). Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); parser tail :456–630 read whole from checkout at fe45b415.
