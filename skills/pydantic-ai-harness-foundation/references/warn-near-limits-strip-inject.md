<!-- capsule-v2 -->
# WarnNearLimits: strip-then-inject model warnings as user turns

## Source / Question
`pydantic_ai_harness/compaction/_warn_near_limits.py` — How do you tell the MODEL it is running out of budget — reliably, once, at the right severity — when every injected warning becomes part of the history the next injection must not duplicate? Porters forget the strip pass or inject as system text the model ignores.

## Path / Symbol
`compaction/_warn_near_limits.py` — `WarningKind = 'iterations'|'context_window'|'total_tokens'` + `_WARNING_ORDER` (23–29), `_MARKER='[WarnNearLimits]'` / `_LEGACY_MARKER='[LimitWarner]'` (30–33, pre-rename histories still stripped), `_Warning(kind, severity URGENT|CRITICAL)` (36–40), config validation (150–186), `_strip_old_warnings` (196–222), warning builders (225–266), `_format_warning` (268–280), `before_model_request` (283–321).

## Signature
```python
messages = self._strip_old_warnings(list(request_context.messages))  # ALWAYS first
active = [w for w in (iteration, context, total) builders if w]       # fixed kind order
messages.append(ModelRequest(parts=[UserPromptPart(content=warning_text)]))
```

## Data Shape
One trailing `ModelRequest` holding ONE `UserPromptPart` whose text starts with `[WarnNearLimits]`, then a severity line, one `- detail` bullet per active warning, then guidance. Threshold `warning_threshold=0.7` fraction; iterations go CRITICAL when remaining ≤ `critical_remaining_iterations` (default 3); context/total go CRITICAL at usage ≥ limit.

## Decisive source
1. **User-turn channel** (:44–48): the warning rides a UserPromptPart "so that the model treats it as a distinct user turn (models tend to pay more attention to user messages than system messages)".
2. **Strip-before-decide** (:52–54, :196–222): previous warnings are stripped BEFORE evaluating thresholds so stateless re-evaluation can't accumulate duplicates. Strip keeps already-empty ModelRequests: pydantic-ai's empty-response retry appends a partless request and dropping it "would leave history ending on a ModelResponse, which fails the next request's 'must end with a ModelRequest' precondition" (:205–210).
3. **Legacy marker tolerance**: `[LimitWarner]` (pre-rename name) still stripped from resumed histories (:30–33) — old persisted sessions don't grow duplicate new-style warnings.
4. **Deterministic ordering**: active warnings sort by `_WARNING_ORDER` regardless of evaluation order (:314–315).
5. **Config coherence**: `warn_on` subset may reference only CONFIGURED limits; exactly one of tokens/fraction per kind; at least one limit total (:160–186).

## Flow / Invariant
Strip → evaluate three independent builders against ctx.usage + anchored context estimate → if none active, write back stripped messages and return → else sort, format (severity = CRITICAL if ANY critical), append single user-turn request. Invariant: at most ONE warning message exists in history at any time; severity escalates automatically near exhaustion; guidance text differs URGENT ("complete efficiently") vs CRITICAL ("complete immediately").

## Probe (direct test)
`tests/compaction/test_compaction.py::TestWarnNearLimits`: `test_no_warning_below_threshold` (:473), `test_iteration_warning_urgent` (:483), `test_iteration_warning_critical` (:500), `test_strips_old_warnings` (:533), `test_strips_legacy_limit_warner_markers` (:544), `test_multiple_warnings_ordered` (:555); edge cases :866–1044 (empty-request preservation :912, non-string prompt not misdetected as marker :1015).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'WarnNearLimits _strip_old_warnings UserPromptPart'`

## Verdict
**Adopt** the strip-then-inject idempotence pattern + user-turn channel for any recurring model-facing notice (deadlines, budget, policy reminders). **Adapt** kinds/severity ladder to your limits.
