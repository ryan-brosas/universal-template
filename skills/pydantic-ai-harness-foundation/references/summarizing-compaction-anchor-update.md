<!-- capsule-v2 -->
# SummarizingCompaction: anchored incremental summaries, bridge prefixes, kept-user retention, deterministic receipts

## Source / Question
`pydantic_ai_harness` (MIT) `main@76db3dec`; graph project `mnt-hdd-utopia-inspo-frameworks-pydantic-ai-harness`; all line pins below re-verified at this head. `pydantic_ai_harness/compaction/_summarizing_compaction.py` — How do you replace old conversation turns with an LLM summary WITHOUT summary-of-summary decay, cross-model confabulation, or losing the user's original asks — while keeping cost accounting honest? Porters naively re-summarize the previous summary and drop first-user intent.

## Path / Symbol
`compaction/_summarizing_compaction.py` — `_DEFAULT_SUMMARY_PROMPT` (56–87, six exact sections: Intent/Key decisions/Artifacts/Current state/Next steps/Open questions), `_DEFAULT_INSTRUCTIONS` (89–91), `_SUMMARY_PREFIX` (93), `_INCREMENTAL_UPDATE_INSTRUCTION` (98–102, opencode mechanism), `_BRIDGE_PREFIX` (107, Codex prior art), `_KEPT_USER_MESSAGE_METADATA` (109), `_model_name` (113–123), `_history_model_name` (126–131), `_model_family` (139–154), `_format_messages` (157–182, tool returns capped at 500 chars), `_extract_system_prompts` (198–211), `_extract_previous_summary` (214–226), `SummarizingCompaction` (240–384, incl. the #669 `instructions` field at :319–325 — see summarizer-instructions-field.md), `with_focus` (386–394, braces escaped because prompt goes through str.format), `compact` (396–458), `_kept_user_messages` (460–486), `_truncate` (488–499), `_bound_sequence` (501–527), `_maybe_bridge_prefix` (529–537), `_insert_receipt` (539–570), `before_model_request` (572–604), `_summarize` (606–642).

## Signature
```python
summary = await self._summarize(to_summarize, ctx, previous_summary=_extract_previous_summary(messages))
# prompt += INCREMENTAL_UPDATE_INSTRUCTION + '<previous-summary>\n…\n</previous-summary>'
result: list[ModelMessage] = [summary_message, *extra, *preserved]; result = reinject_pinned(messages, result)
```

## Data Shape
Summary rides as a `SystemPromptPart` whose content starts with `_SUMMARY_PREFIX` — that prefix IS the discovery key for the next incremental round (`_extract_previous_summary` scans reversed history for it, stripping any bridge prefix first). Kept user copies carry `metadata['pydantic-ai-harness.compaction.kept-user-message.v1']=True`. Receipts are receipt-part-only messages (de-accumulated each round). Trigger triple `max_messages | max_tokens | max_fraction` (one required); tail budget `keep_messages` slots or `keep_tokens`.

## Decisive source
1. **Anchored increment** (:98–102, :339–344): the previous summary is fed back as `<previous-summary>` with "Update it using the conversation above: preserve still-true details, remove stale details, and merge in new facts" — updated IN PLACE "rather than a summary to re-summarize, which avoids summary-of-summary decay." When incrementing, `_format_messages(skip_previous_summary=True)` omits the old summary text from the transcript so it isn't double-counted (:616).
2. **Cross-model bridge** (:346–351, :529–537): only on genuine FAMILY mismatch (`_model_family`: drop provider prefix, take token before first `-`/`/`; FallbackModel reduces to its FIRST model) between the history-producing family (`_history_model_name` = most recent ModelResponse.model_name) and the summarizer's — prepend "This summary was produced by a different model than the one continuing the task." Same-family adds nothing; the prefix is stripped again before the next anchor round (:229–231, applied at :225).
3. **Kept-user retention** (:353–358, :460–486): retained summarized user turns CONSUME the `keep_messages` tail budget (bounded), each truncated to `keep_user_messages_max_chars` (head strategy + `[...]` marker, `_truncate` :488–499); sequence-shaped prompt parts share ONE budget across text-bearing items, non-text items (images/cache points) pass through unrewritten (:501–527). Supersedes `preserve_first_user_message`; rebuilt copies are tagged so later passes recognize their own artifacts (:484).
4. **Honest accounting** (:641): the summary call's usage is folded into the parent run via `agent.run(prompt, usage=ctx.usage)` — counts as a real request, so cost AND request-count limiters see it.
5. **Realtime refusal** (:629–634): a realtime `AbstractModel` cannot write summaries → `UserError` demanding an explicit `model=`, never a silent wrong-model call.
6. **Receipts** (:364–371, :539–570): opt-in deterministic receipt inserted right AFTER the summary message; old receipt-shaped messages de-accumulated first; records dropped message/token counts, summarizer family, optional persisted-run handle.

## Flow / Invariant
Gate (exceeds max_messages/max_tokens/max_fraction) → `compact_with_span` → cutoff via `keep_tokens` (token budget) else `find_safe_cutoff(keep_messages)` pair-safe → extract leading system prompts (scan STOPS at first non-request or non-system part — nothing after the first real turn qualifies) → summarize with optional anchor → bridge-prefix decision → assemble `[system+summary, *kept, *preserved]` → `reinject_pinned` → optional receipt insertion. Invariants: tool-call/result pairing never split by the cutoff; the summary is secondhand knowledge (receipt says so); summary prefix grammar is parsed back — treat it as a format contract, not prose.

## Probe (direct test)
`tests/compaction/test_compaction.py` (lines at pin `76db3dec`): `test_extract_previous_summary_found/not_found/empty_messages/skips_non_requests` (:1440/:1447/:1454/:1457), `test_incremental_includes_previous_summary` (:1465), `test_incremental_disabled` (:1535), `test_previous_summary_fed_as_anchor_with_update_instruction` (:3536), `test_same_fallback_model_does_not_add_a_bridge` (:3650), `test_newest_summarized_user_message_is_preserved_and_truncated` (:3310), `test_pin_is_not_rebuilt_as_a_kept_user_message` (:3494), `TestSummarizingReceipts` — `test_receipt_present_and_after_summary` (:3118), `test_receipt_is_byte_deterministic` (:3138), `test_receipts_do_not_accumulate` (:3181), `test_receipt_reserves_a_message_slot` (:3234).

## Retrieve
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-pydantic-ai-harness", query: "SummarizingCompaction previous_summary bridge_prefix", limit: 10 });
```
(CLI-equivalent verified live at `76db3dec`: rank#1 `_maybe_bridge_prefix` :529–537, then `_without_bridge_prefix` :229–231 and `_extract_previous_summary` :214–226; short-name twin project `pydantic-ai-harness` serves the identical refreshed graph.)

## Verdict
**Adopt** the anchored-increment pattern (anchor + update instruction + prefix-as-grammar) for any recurring summarizer. **Adopt** family-mismatch bridge notes and kept-user budget consumption as cheap anti-intent-loss guards. **Adapt** the six-section prompt to your domain; keep the `{messages}` placeholder contract.
