<!-- capsule-v2 -->
# Policy Matcher — who wins when keyword, natural-language, guard, and playbook policies collide on one input?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What is the exact precedence order and confidence arithmetic for picking the single best policy match — including what happens when the LLM judge fails?

## Two-track evaluation with IntentGuard precedence
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/agent.py` (`_check_trigger` :169-323, `_evaluate_keyword_triggered_policies` :697-777, `_evaluate_natural_language_policies` :779-928, `match_policy` :930-1043, `_resolve_nl_trigger_conflicts` :536-695, `_min_nl_threshold` :520-523, `_fallback_confidence` :525-534).

**Signature:** `async match_policy(context: PolicyContext, target: str = "intent", policy_types: Optional[List[PolicyType]] = None) -> PolicyMatch`.

**Data Shape:** Returns `PolicyMatch{matched, policy, action, confidence∈[0,1], reasoning, trigger_details}`. Keyword track returns `(policy, confidence, reasoning, trigger_details)` where AND-match confidence is 1.0 and OR-match confidence is matched/total keyword fraction.

### Decisive source
```python
# agent.py:992-1008 — IntentGuard beats everything at equal confidence;
# among non-guards pure confidence wins.
for policy, confidence, reasoning, trigger_details in candidates:
    if isinstance(policy, IntentGuard):
        if not best_match or not isinstance(best_match, IntentGuard):
            best_match = policy ...          # guard takes precedence outright
        elif confidence > best_confidence:
            best_match = policy ...          # better guard replaces guard
    elif not best_match or (
        not isinstance(best_match, IntentGuard) and confidence > best_confidence
    ):
        best_match = policy ...
```
And the clamp that keeps matches alive (`agent.py:1019-1028`, comment quoted):
> "When both keyword and NL triggers fire on the same policy, the combined score can land at 1.0000000000000002 (float rounding); without the clamp PolicyMatch validation raises and the whole match is silently lost inside the `except` below."
`confidence=min(1.0, max(0.0, best_confidence))`

**Flow:** `match_policy` → keyword track (IntentGuard policies checked before others when target=="intent", :747-756; highest-confidence all-triggers-match wins) ∥ NL track (embed query → vector search limit 20 → sort candidates by (in-vector-set, priority) :856-858 → LLM conflict resolution picks 1-based index or null → selected policy's confidence must clear its own min NL threshold → remaining non-NL triggers must ALL still match with `skip_nl_triggers=True`) → merge candidates under IntentGuard-first rule.

**Invariant:** LLM failure ≠ no match. In `_resolve_nl_trigger_conflicts`' exception handler (:684-693): a *successful* "no match" verdict or below-threshold verdict returns None, but an *exception* falls back to candidate index 0 at exactly its min-NL-threshold confidence ("Error in conflict resolution, using first policy"). The comment notes this makes a parse error MORE likely to fire a policy than a working model that rejects — intentional fail-toward-enforcement. No LLM at all ⇒ NL track returns None (:865-867).

**Probe:** `src/cuga/backend/cuga_graph/policy/tests/test_keyword_operator.py` (AND/OR/case pins: :57-58 confidence 1.0 for full AND, :73 no-match partial AND, :144 OR any-keyword); `test_nl_trigger_conflict_fallback.py:68 test_conflict_resolution_error_fallback_meets_threshold` asserts fallback confidence equals the strictest threshold so it survives gating ("fallback was discarding matches with confidence 0.5 < threshold 0.7"), plus `:288 test_conflict_resolution_fallback_uses_first_of_multiple_policies`; precedence pinned by `test_e2e_intent_guard_priority.py:28 test_intent_guard_priority_over_playbook`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_resolve_nl_trigger_conflicts fallback first policy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-track matching, type-based precedence over numeric priority for blocking rules, threshold-gated LLM adjudication, and the exception→first-candidate-at-threshold fallback (with its fail-toward-enforcement rationale). Adapt embedding/vector-store details. Omit the debug-level per-trigger logging if you don't need audit noise.
