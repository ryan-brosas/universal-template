<!-- capsule-v2 -->
# Output Formatter — post-answer policy that can replace, reformat, or restructure the agent's final message

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you transform the final AI message per policy — including hard replacement for sensitive-data blocking — without the LLM "helpfully" preserving what you asked it to redact?

## Three format modes + instructions-take-precedence prompting
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/enactment.py:870-1091` (`_enact_format_output`); application helper `src/cuga/backend/cuga_graph/policy/output_formatter_utils.py:19-118` (`apply_output_formatter_policies` :19, `_update_output_formatter_metadata` :77).

**Signature:** `async _enact_format_output(state, policy_match, policy_system, context) -> tuple[None, Dict[str, Any]]` (metadata only; caller writes `state.final_answer`).

**Data Shape:** `OutputFormatter{format_type: "markdown"|"json_schema"|"direct", format_config: str}`. Metadata produced: `{policy_matched, formatted_response, original_response, format_type, ...}`.

### Decisive source
```python
# enactment.py:943-962 — direct mode needs no LLM; markdown mode's prompt was
# fixed after CI failures where "preserve all facts" fought redaction rules:
if format_type == "direct":
    formatted_content = format_config          # verbatim string replacement
elif format_type == "markdown":
    # format_config is authoritative. The previous "preserve all facts / do not
    # remove details" rules fought replace/redact instructions and caused CI
    # failures when markdown mode was used for sensitive-data blocking.
    system_prompt = f"""You are an output formatter. Transform the AI's response according to these instructions:

{format_config}

Important:
- Follow the instructions above exactly; they take precedence over every other rule here
- If the instructions say to replace, redact, withhold, or block content, do that — do not keep the original wording
- Otherwise, only change formatting/structure/presentation and do not invent new facts
- Preserve citation markers like [s3] verbatim and attached to the same claims; never renumber, drop, or invent them (unless the instructions require removing or replacing the response entirely)"""
```
json_schema path (:1024-1031): `llm.with_structured_output(schema, method="json_schema")`, dict result re-dumped with indent 2; on structured-output failure falls back to a plain prompt; invalid JSON schema in config ⇒ `(None, None)` (:1066-1068).

**Flow:** final answer exists → `apply_output_formatter_policies(state, config, context=...)` (called from `cuga_lite_node.py:372`) → `check_and_enact(policy_types=[OUTPUT_FORMATTER])` matches triggers against target text that COMBINES user input + agent response (`PolicyContext.get_target_text`, `agent.py:99-103`) → metadata.formatted_response written back to `state.final_answer` + UI metadata (`output_formatter_applied`, original kept for audit).

**Invariant:** The formatter's LLM must treat `format_config` as supreme authority or redaction/blocking policies are unsafe (the quoted comment documents real regressions). Citation-marker preservation is deliberately conditional — "unless the instructions require removing or replacing". Last-AI-message resolution order: last AIMessage in chat_messages → context.agent_response → state.final_answer (:902-922).

**Probe:** `src/cuga/backend/cuga_graph/policy/tests/test_e2e_output_formatter.py` — 5 e2e cases incl. `:661 test_e2e_output_formatter_sensitive_data_blocking` and `:478 json_schema_structured_output`; `test_policy_observability.py` pins decision records at OUTPUT stage.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_enact_format_output markdown json_schema direct", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt direct/markdown/json_schema modes, the instructions-take-precedence prompt contract, and write-back via `final_answer` with original retained in metadata. Adapt prompt wording/model choice. Omit chat-history conditioning (last 10 messages) if your formatter should stay memoryless.
