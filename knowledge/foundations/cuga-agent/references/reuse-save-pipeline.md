<!-- capsule-v2 -->
# ReuseAgent save pipeline — how does a consolidated flow become saved code + optional HTML with graded partial-success messages?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What is the exact failure ladder when consolidating/reusing a flow, and how is the LLM's token budget raised just for HTML generation?

## Four-outcome save ladder with per-instance max_tokens lift
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/save_reuse/save_reuse_agent/reuse_agent.py:ReuseAgent.__init__` (:34-64), `run` (:93-166), `get_text_after_last_backticks` (:70-78); consolidation seam already mined in `trajectory-consolidation.md` (consolidate_flow returns None when no code steps exist).
**Signature:** `run(input_variables: AgentState, additional_utterance="") -> AIMessage`; `max_tokens: int = 15000` constructor default.
**Data Shape:** outputs = AIMessage whose content starts ✅ / ❌ / ⚠️ ("Partially saved") and always ends with `get_text_after_last_backticks(res.content)` (model's own explanation after its last fence). Artifacts: `PACKAGE_ROOT/backend/server/flows/flow.html`, `PACKAGE_ROOT/backend/tools_env/registry/mcp_servers/saved_flows.py`.

### Decisive source
```python
        if hasattr(llm, 'max_tokens'):
            llm.max_tokens = max_tokens
        if hasattr(llm, 'max_completion_tokens'):
            llm.max_completion_tokens = max_tokens
        if hasattr(llm, 'model_kwargs') and llm.model_kwargs is not None:
            llm.model_kwargs['max_tokens'] = max_tokens
```
and the outcome ladder:
```python
        if res is None:
            return AIMessage(content="⚠️ Cannot save this flow for reuse.\n\nReason: This flow didn't involve any code generation steps ...")
        pattern = r'```python\s*\n(.*?)\n```'
        matches = re.findall(pattern, res.content, re.DOTALL)
        if not matches:
            return AIMessage(content="❌ Failed to save flow for reuse....")
```

**Flow:** consolidate_flow(chain, input+utterance) → None ⇒ friendly refusal (no code steps ever recorded); python fence regex finds nothing ⇒ ❌ with tail text; HTML gen only when `settings.advanced_features.save_reuse_generate_html` — html fence missing ⇒ ⚠️ partial (code OK, HTML failed); `process_text_file(...)` False ⇒ ⚠️ partial; success ⇒ ✅ with both artifact paths. The vischain shares the SAME llm instance — that's why the three-attribute max_tokens sweep happens in __init__.
**Invariant:** All four outcomes return a MESSAGE (never raise) — the chat HITL surface renders them verbatim; the tail-extraction helper keeps the model's explanation visible even in failure paths. The max_tokens lift must cover every provider attribute or long HTML silently truncates.
**Probe:** Recorded upstream gap (consolidation side pinned by trajectory-consolidation's probes). Deterministic: `grep -n "save_reuse_generate_html" src/cuga/backend/cuga_graph/nodes/save_reuse/save_reuse_agent/reuse_agent.py` hits the flag check :116.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ReuseAgent consolidate_flow process_text_file save_html_to_file", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt graded partial-success messaging for multi-artifact generation and the constructor-time provider-attribute budget lift. Adapt artifact destinations. Omit HTML visualization by keeping the flag off (upstream treats it as optional enhancement).
