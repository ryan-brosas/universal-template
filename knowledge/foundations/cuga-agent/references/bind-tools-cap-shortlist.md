<!-- capsule-v2 -->
# Bind-tools cap and shortlist — how do you cut an over-cap tool list down WITHOUT silently truncating, while guaranteeing a protected meta-tool survives?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When candidates exceed the provider-safe cap (~128 for Groq/OpenAI), what is the exact reduce pipeline, and how does `find_tools` survive an LLM ranker free to drop it?

## apply_bind_tools_cap_and_merge
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/bind_tools/cap.py:87-383` (`_resolve_find_tools_overlay`, `_build_ranking_pool`, `_run_shortlister`, `_materialize_shortlist`, `_maybe_pad_to_cap`, `apply_bind_tools_cap_and_merge`), settings readers :46-84.
**Signature:** `async apply_bind_tools_cap_and_merge(bound, *, query, tool_provider, llm, max_count, include_find_tools, tools_context_ref, mode, run_config=None) -> List[StructuredTool]`.
**Data Shape:** cap default 128 (`bind_tools_max_count_from_settings`, 0/negative = disabled); pad-to-cap opt-in default False.

### Decisive source
```python
# _resolve_find_tools_overlay (:97-101): explicit opt-out beats overlay injection
# If the user disabled it but the overlay injected it anyway, strip it from
# ``bound`` so it can't consume a capped slot or sneak into the shortlister's input.
if not include_find_tools and find_tools_already_in_bound:
    bound = [t for t in bound if getattr(t, "name", "") != find_tools_name]

# _build_ranking_pool (:126-130): survival by removal-then-append
# When ``include_find_tools=True`` the LLM ranker is free to drop any tool from
# the ranking pool — pulling find_tools out and appending it back is the only
# safe way to guarantee it.
...
reserve = 1 if keep_find_tools else 0
target_k = max_count - reserve
```

**Flow:** reconcile find_tools (strip if opted-out-but-injected) → build ranking pool without find_tools when it must be guaranteed → under cap ⇒ append find_tools back and return → over cap with NO query ⇒ **RuntimeError** with three remediation options (non-empty first message / raise env-var cap / set 0) → shortlister top-K (= cap − reserve) → map names back to tools with a defense-in-depth clamp at the call site ("without this clamp the bound list could exceed ``max_count`` and re-trigger the provider 400") → zero matched names ⇒ RuntimeError naming the hallucination → optional padding to fill the cap → re-append find_tools.
**Invariant:** (1) silent truncation corrupts benchmark comparisons — every reduction failure is loud; (2) a must-survive tool is guaranteed structurally (remove from rankable pool + reserved slot), never by prompt-nagging; (3) padding defaults OFF because measured regressions: binding many tools pushes the model into native `tool_calls` mode which the code-act flow doesn't exercise ("measured: 0 tool calls vs 5-7 without padding on the m3 hockey benchmark"); (4) clamp enforces target_k AGAIN even though the prompt says top_k — mocked/custom shortlists can lie.
**Probe:** no direct unit test (coverage caveat — deterministic checks: 129 tools + cap 128 + no query ⇒ RuntimeError mentioning all three options; ranker returning only unknown names ⇒ RuntimeError with sample_ranked; find_tools excluded from ranking pool but present in final list). The loud-failure contract is cross-pinned by helpers/bind_tools.py's re-raise ladder.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "apply_bind_tools_cap_and_merge _materialize_shortlist target_k", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reserve-a-slot removal pattern for protecting meta-tools through any lossy LLM selection step, and the loud-not-silent reduction failures; adapt cap defaults and padding policy to your providers; omit padding entirely unless you run native-FC research modes. Coverage caveat: source-read verified; error strings are the executable spec here.
