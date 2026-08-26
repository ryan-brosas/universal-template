<!-- capsule-v2 -->
# Unverified-blocker override — when may a harness contradict an LLM's refusal, and how do you keep the override from becoming a forced-labor loop?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (#657/#610); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** The model emits "I'll discover the Spotify tool first… I'm sorry, but I couldn't access…" and finalizes after 2 LLM calls with ZERO executed calls. When is overriding that finalize provably safe?

## BlockedClaimEvidence + one-shot corrective retry
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/nl_auto_continue_classifier.py:115-166` (`_BLOCKED_CLAIM_RE`, `BLOCKED_CLAIM_CORRECTION`, `BlockedClaimEvidence`, `looks_like_unverified_blocker`), `:257-266` (`_blocked_override_applies`), `:268-338` (`classify_nl_auto_continue_decision` — override fires ONLY on a confirmed `False` verdict); harness side `adapter/graph_adapter.py:211-241` (`classify_auto_continue` returns `bool | str`, `_blocked_claim_retry` marker, `_any_execution_ran`); contract widening `cuga_agent_core/graph/graph_nodes.py:181-194` + synthetic-message consumption `shared_nodes.py:303-315`.
**Signature:** `async classify_auto_continue(state, model, content, reasoning) -> bool | str` (non-empty str = corrective directive used verbatim as the synthetic user message).

### Decisive source
```python
# nl_auto_continue_classifier.py:257-266 — ALL conditions must hold
def _blocked_override_applies(visible, reasoning, evidence):
    """The unverified-blocker override (issue #610): all conditions must hold."""
    if evidence is None:
        return False
    if not getattr(settings.advanced_features, "cuga_lite_blocked_claim_retry", True):
        return False
    if not evidence.tools_available or evidence.code_executed or evidence.retry_used:
        return False
    return looks_like_unverified_blocker(visible, reasoning)
```
```python
# classifier.py:320-330 (decision fn tail) — ONLY an explicit False reaches it
    # The classifier explicitly chose finalize (parsed False). Only that verdict
    # reaches the override — a classifier error or unparsable output finalizes
    # above, exactly like the pre-existing bool path, so the override never
    # fires on anything but a confirmed finalize.
    if _blocked_override_applies(visible, reasoning, evidence):
        return AutoContinueDecision(auto_continue=True, blocked_override=True)
    return finalize
```

**Flow:** regex detects inability claims (`couldn't|unable to|cannot + access|locate|retrieve…`, "no available/such/suitable tool", "lacks a tool" — the last two added verbatim from observed gpt-oss-120b failures the first clauses missed). The harness supplies POSITIVE evidence: tools bound this turn, zero executions ever (detected by scanning HumanMessages for the shared `EXECUTION_OUTPUT_PREFIX` constant), retry unspent. On fire: adapter stamps `_blocked_claim_retry` into metadata ONE-SHOT and returns the correction string; `shared_nodes` uses it as the synthetic HumanMessage INSTEAD of bare "continue" (a bare continue elicits the same refusal) and REBUILDS metadata after classify because the snapshot was taken before the call mutated state. A second refusal finalizes.

**Invariant:** (1) Override requires CONFIRMED finalize — LLM-classifier error/unparsable output finalize WITHOUT override (fail-closed). (2) One-shot only: a spent marker makes `retry_used` True forever after, so the loop can't force the model past a genuine failure. (3) Refusal AFTER real attempts is legitimate — `code_executed=True` disables the override entirely; this is deliberately NOT `require_tool_call_before_final` (removed in PR #416 review) because tool-free completions ("what can you do?") contain no inability claim and must still finalize. (4) `bool` wrapper path never overrides — legacy callers get unchanged behavior. (5) The str-return contract is additive: base adapters return False; truthy-str handling lives in shared_nodes so both graph families share one consumption point.

**Probe:** direct tests `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_nl_auto_continue_classifier.py::test_observed_blocker_strings_detected` (:137), `::test_non_blocker_text_not_detected` (:155), `::test_blocked_override_fires_on_turn1_refusal` (:173), `::test_blocked_override_requires_positive_evidence` (:189), `::test_bool_wrapper_never_overrides` (:223), `::test_blocked_override_requires_confirmed_finalize_verdict_on_error` (:230), `::test_blocked_override_requires_confirmed_finalize_verdict_on_unparsable` (:244); adapter wiring `tests/test_agent_graph_adapter.py` (blocked-claim cases); prefix constant pinned via `tests/unit/` shared-graph suites asserting `EXECUTION_OUTPUT_PREFIX`.

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "BlockedClaimEvidence _blocked_override_applies BLOCKED_CLAIM_CORRECTION classify_nl_auto_continue_decision", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT when an agent loop may finalize on a refusal the runtime can POSITIVELY falsify: demand independent evidence for every precondition, spend exactly one corrective turn with specific instruction text (never bare "continue"), and let every error path fail closed toward finalize.
