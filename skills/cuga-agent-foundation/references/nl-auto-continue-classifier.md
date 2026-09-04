<!-- capsule-v2 -->
# NL auto-continue classifier — how do you detect the "planning-text stall" (agent narrates instead of coding) without trusting a flaky LLM call?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (refreshed pass 18: #657 split the decision fn and added the unverified-blocker override — see blocked-claim-retry-override capsule); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When a code-agent turn contains prose but no fenced Python, do you auto-continue — and how do you make that decision cheap, safe, and fail-closed?

## Deterministic fast-path first, LLM classifier second, parse-failure ⇒ finalize
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/nl_auto_continue_classifier.py:69-190` (`_PLANNING_INTENT_RE`, `looks_like_planning_text`), `:193-253` (`build_combined_content_and_reasoning`, `parse_auto_continue_json`), `:268-338` (`classify_nl_auto_continue_decision` — the real body), `:341-349` (`classify_nl_auto_continue` kept as a thin bool WRAPPER delegating to the decision fn).
**Signature:** `looks_like_planning_text(visible: str) -> bool`; `async classify_nl_auto_continue_decision(llm, assistant_visible, reasoning_excerpt, *, evidence: Optional[BlockedClaimEvidence] = None) -> AutoContinueDecision`; legacy `async classify_nl_auto_continue(...) -> bool` unchanged.
**Data Shape:** Transcript caps: visible 12k / reasoning 8k / combined 20k chars; combined block labels sections (`## Assistant content (user-visible)` / `## Reasoning (internal)`); verdict is strict JSON `{"auto_continue": bool}`.

### Decisive source
```python
# nl_auto_continue_classifier.py:54-62 — why the regex path exists
# The agent occasionally emits a short first-person plan with no code ...
# The LLM classifier has been observed to misfire on these and finalize the
# plan as the answer (the "planning-text stall"). We catch the unambiguous
# cases here so the result does not depend on a flaky model call.
# This path is intentionally conservative: it only flips False -> True for short
# text that opens with a first-person intent ... followed by a forward-looking
# action or modal verb. ... the surrounding graph already enforces a step limit
# before auto-continuing, so an over-fire cannot loop forever.
```
The fast-path GUARDS are as load-bearing as the match: length ≤400 chars; no trailing `?` (questions must finalize); `_NEGATION_RE` ⇒ fall through ("I could not find…" is a result, not a plan); `_SECOND_PERSON_RE` ⇒ fall through ("…but first I require your ID" must reach the USER, not a synthetic continue). Only then does the LLM see content+reasoning combined — reasoning matters because platforms that provide CoT reveal intent invisible text can't. Every degenerate outcome finalizes: unparsable JSON, empty transcript, config off, ANY exception ⇒ `False` (never loops on a broken classifier).

**Flow:** no-code turn → normalize content blocks → fast-path regex gate (True ⇒ synthetic `continue`) → combined-transcript LLM classify → strict JSON extract (fence-stripping + brace-span) → True appends `HumanMessage("continue")` and re-invokes; anything else ends the graph normally. Since #657 the bool verdict is really `AutoContinueDecision(auto_continue=...)`, and a confirmed `False` can be upgraded to a corrective-str continue by the unverified-blocker override — but every error/unparsable path still finalizes without it.
**Invariant:** Auto-continue may only flip False→True deterministically or via a healthy classifier; classifier sickness must degrade to FINALIZE (stop), never to loop; second-person/negation/question text always escapes the fast-path because continuing there would answer FOR the user.

**Probe:** `tests/unit/test_langfuse_tracing.py::test_nl_auto_continue_passes_invoke_config` — pins the full classifier path end-to-end: strict-JSON `{"auto_continue": false}` parsed to a False verdict AND the nested LLM call receiving the synced Langfuse callback config. Decision-fn split pinned by `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_nl_auto_continue_classifier.py::test_bool_wrapper_never_overrides` (:223).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "classify_nl_auto_continue_decision looks_like_planning_text", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier design (conservative deterministic fast-path over a guarded LLM classifier) with fail-closed finalize semantics. Adapt regex vocabulary to your agent's phrasing. Omit reasoning ingestion if your platform exposes none.
