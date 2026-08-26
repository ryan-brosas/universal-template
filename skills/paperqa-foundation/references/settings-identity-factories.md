<!-- capsule-v2 -->
# Settings identity & model factory — how does one config object name its index, price its run, and build every LLM?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How is a Settings object fingerprinted (md5) so sessions record their config, how does the index NAME encode parsing strategy, and why does every get_llm wrap models in a single-entry LiteLLM router list?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/settings.py:Settings.md5` (:843-846), `get_index_name` (:853-874), `get_llm/get_summary_llm/get_agent_llm/get_embedding_model/get_enrichment_llm` (:925-960), `make_default_litellm_model_list_settings` (:728-747), `PromptSettings` validators via `get_formatted_variables` (:388-403, :454-518).
**Signature:** `def md5(self) -> str` (computed_field); `def get_index_name(self) -> str` returning `pqa_index_{hexdigest('|'.join(segments))}`.
**Data Shape:** Index-name segments = [abs(paper_directory), use_absolute_paper_directory, embedding, stable_str(parse_pdf, for_hash=True), chunk_chars, overlap, full_page, multimodal] — i.e. the FULL parse+embed strategy; two configs sharing a name share cached parsings.

### Decisive source
```python
return {
    "name": llm,
    "model_list": [{
        "model_name": llm,
        "litellm_params": {"model": llm, "temperature": temperature,
            # prompt-caching: system message pinned as cache breakpoint
            "cache_control_injection_points": [{"location": "message", "role": "system"}]},
    }],
}
...
for model_prefix in ("o1", "gpt-5"):
    if self.llm.startswith(model_prefix) and self.temperature != 1:
        warnings.warn(...)  # o1/gpt-5 REQUIRE temperature=1 — silently overridden
        self.temperature = 1
```
Prompt-variable validation (`_FormatDict.__missing__` records unknown keys then format_map proceeds): custom summary/qa/select/context prompts may only USE variables the canonical template defines; context_inner MUST contain {name} and {text}; post may reference any PQASession field.

**Flow:** config_md5 stamped onto every PQASession at creation → reproducibility + cache keys; from_name resolves user `~/.pqa/settings/{name}.json` → bundled `paperqa.configs` package fallback with json-validate-then-dump roundtrip (types survive); get_settings accepts Settings | dict | name | None.
**Invariant:** The md5 EXCLUDES itself but nothing else — any settings change invalidates session comparability by design; index names must include parser FQN hash because parsers produce different text from identical bytes.
**Probe:** `tests/test_configs.py` (config roundtrips); executed grep pins temperature-override :830-841 and cache_control injection :741-743.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "get_index_name make_default_litellm_model_list_settings get_formatted_variables", limit: 10 });
```

## Verdict
Adopt strategy-encoded index names + router-list default + prompt-variable subset validation; adapt segment list to your parser registry; omit ldp-agent factories if you have no RL agents. Coverage caveat: cited tests live in test_configs.py requiring install extras.
