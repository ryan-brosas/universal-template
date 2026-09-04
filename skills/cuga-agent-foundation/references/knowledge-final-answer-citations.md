<!-- capsule-v2 -->
# FinalAnswer citation application — idempotent resolution fused with harmony-token stripping on every terminal path

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where in the answer pipeline do [sN]→[n] resolution and control-token cleanup run, how do they stay idempotent under supervisor re-entry, and why can they never break delivery?

## apply_citation_resolution
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/answer/final_answer.py` (`apply_citation_resolution` :82-136; HITL default-fallback call site :43-47); token filter `src/cuga/backend/cuga_graph/utils/harmony.py` (`harmony_special_tokens` lru_cached; `strip_harmony_tokens`; `_FALLBACK_CONTROL_TOKENS`; text-driven gate `harmony_handling_enabled`).
**Signature:** `FinalAnswerNode.apply_citation_resolution(state) -> None` (mutates `state.final_answer`, `state.sources`).
**Data Shape:** runs AFTER variable-placeholder replacement and output formatters, at EVERY terminal path (node_handler paths ×5+, HITL default fallback) — "every other terminal path already guards this" is the review invariant.

### Decisive source
```python
# :110-123 — cheap substring guard; already-resolved detection keeps first-pass sources
if "<|" in text:
    text = strip_harmony_tokens(text)
    state.final_answer = text
if not has_citation_markers(text):
    already_resolved = bool(state.sources) and _re.search(r"\[\d+\]", text) is not None
    if not already_resolved:
        state.sources = []          # stale prior-turn sources must not ride along
    return

# :133-136 — total failure still sanitizes state
except Exception:
    state.sources = []
    logger.exception("citation resolution failed; delivering unresolved answer")
```

**Flow:** substring-fast-path harmony strip (decode boundary `normalize_response` owns the real cleanup; this is defence-in-depth for answers assembled from other sources — one `"|<"` check when idle) → no `[sN]` markers: keep sources only if the text carries resolved `[n]` chips (supervisor callback re-entering with an already-resolved `last_planner_answer` — MAJ-2), else clear stale → citations enabled for thread? resolve via ledger : strip-mode removes markers silently → ANY exception clears sources and delivers the unresolved answer.
**Invariant:** The harmony gate is a KILL SWITCH driven by the TEXT (`"<|" in text`), never by configured model name — CugaLite resolves a different model than the final-answer agent and names lie (proxies, prefixes, published llm_config). Vocabulary comes from the openai-harmony encoding with a frozen 8-token fallback so a stripped install degrades instead of disabling. Unreadable settings leave the filter ON. Idempotency: second entry must KEEP first-pass sources (only exact `[n]`-with-existing-sources counts as resolved).
**Probe:** direct tests `tests/unit/test_final_answer_citations.py::test_idempotent_keeps_sources_on_already_resolved_text` (:213), `::test_resolution_errors_never_break_the_answer` (:154), `::test_disabled_citations_strip_markers_instead_of_resolving` (:140), `::test_gate_is_a_kill_switch_not_a_model_check` (:240), `::test_vocabulary_falls_back_when_openai_harmony_is_missing` (:279), `::test_unreadable_settings_leave_the_filter_on` (:265), `::test_hitl_default_fallback_clears_stale_sources` (:189), `::test_legitimate_special_token_text_is_preserved` (:69).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "apply_citation_resolution strip_harmony_tokens harmony_handling_enabled FinalAnswerNode", limit: 10 });
```

## Verdict
Adopt one static mutator called from every terminal path with try/except that degrades to "deliver unresolved + clear sources", the text-driven kill-switch gate with upstream-sourced vocabulary, and the already-resolved keep-guard. Adapt which terminal paths exist in your graph — but port the rule that a terminal path added later MUST call it (the HITL fallback bug). Omit gpt-oss specifics if your providers normalize all channels.
