<!-- capsule-v2 -->
# Guardrail verdict contract: five actions, threading chains, read-only guard input, approval round trip

## Source / Question
`pydantic_ai_harness/guardrails/_shared.py` + `_tool_guardrail.py` (+`_capability.py`) — What is the minimal verdict vocabulary that makes ONE guard type compose across input/output/tool edges without ambiguity about what happened to the value — and what does a host get wrong wiring it into the tool loop? Porters conflate block/retry, let guards mutate their input while reporting allow, or defer approved calls forever.

## Path / Symbol
`guardrails/_shared.py` — `_Unset/_UNSET` (19–29), `GuardrailResult` (32–133, per-action validation in `__post_init__`), classmethods allow/block/replace/retry/approve (135–176), `takes_ctx` (185–198, parameter COUNT not annotation), `evaluate` (200–209, bool normalize True→allow/False→block), `is_guard_chain` (218–231), `as_guards` (239–261), `evaluate_all` (263–300), zero-duration span helpers `trace_block/trace_redaction/trace_approval` (306–326). `_tool_guardrail.py` — args-stage `before_tool_execute` (326–387), failure-screening `wrap_tool_execute` (389–418), `_screen_failure` (420–462), result-stage `after_tool_execute` (464–505), unmatched-selector warnings (`_warn_unmatched_names` :308–324).

## Signature
```python
@dataclass(frozen=True, kw_only=True)
class GuardrailResult:
    action: Literal['allow','block','replace','retry','approve']
    message: str | None = ...        # block refusal / retry instruction
    replacement: object = _UNSET     # sentinel, NOT None — replace(None) is legal

async def evaluate_all(guards, ctx, value, *, check_replacement=None) -> tuple[GuardrailResult, int]
```

## Data Shape
Verdict legality matrix enforced at construction: allow/approve take NOTHING; replace REQUIRES a replacement and forbids message; retry REQUIRES message, forbids replacement; block takes optional message and FORBIDS replacement ("nothing reads it here, so accepting one would silently discard a substitution the guard believed it had made"). Input rejects retry+approve; output rejects approve; tool RESULT stage rejects approve ("the tool has already run"). Chain field accepts one callable or a Sequence — str/bytes excluded (would split into characters), sets refused (no order), iterators refused (spent after first run).

## Decisive source
1. **Chain threading** (:263–300): `replace` substitutes the value the REST of the chain inspects — "a redactor followed by a checker sees the redacted text"; every other outcome ENDS the chain (nothing left to judge). All-allowed-with-at-least-one-replace ⇒ accumulated replacement is the verdict. `check_replacement` validates AT SUBSTITUTION TIME so the offending guard is NAMED (position returned for error messages).
2. **Read-only tool args** (_tool_guardrail :337–346): `MappingProxyType(deepcopy(args))` — the dict IS the one the tool will be called with, so an in-place mutation "would change the call while reporting `allow`, bypassing both the replace contract and its span"; the proxy alone stops only TOP-LEVEL writes, hence the deepcopy before wrapping.
3. **Approval round trip** (:366–380): `approve` raises ApprovalRequired unless `ctx.tool_call_approved` — "a resumed run re-evaluates the guard, and a policy that asked for approval once asks again. Honoring `tool_call_approved` … is what ends the round trip instead of deferring the call forever." A resumed call may still be blocked by the same guard (:316 test).
4. **Failure screening keeps the exception type** (:400–418, :420–437): ModelRetry/ToolFailed bypass `after_tool_execute` (core wraps and re-raises past it) yet their text lands in conversation — screened inside the WRAP instead; "a failure screened into a refusal is still a failure" (type preserved, content swapped; :544 test). Retry-on-failure still raises ModelRetry — collapsing to a replacement "would skip the run's retry accounting" (:443–446).
5. **Telemetry discipline**: refusals/redactions/approvals record ZERO-DURATION spans; message/original/arguments attach ONLY under `trace_include_content` ("ops audiences are broader than the user who sees the refusal text"); approval span carries tool_call_id because deferral means NO execute_tool span ever exists — it's the only record of what was asked.
6. **Selector hygiene**: `tools=`/`hidden=` names that never matched any offered tool warn AFTER the run (:308–324) — a typo'd name silently unguards everything otherwise.

## Flow / Invariant
args stage: guard sees frozen copy → allow passthrough / block SkipToolExecution(message)=refusal result / retry ModelRetry / approve ApprovalRequired (flag-gated) / replace validated-mapping + redaction span → handler. Result stage mirrors on outputs; failure path screens in wrap. Invariants: exactly one way to change a value (replace, spanned); guards can't lie by mutation; approve is argument-stage-only; every non-allow leaves a span.

## Probe (direct test)
`tests/guardrails/test_tool_guardrail.py`: `test_block_substitutes_a_refusal_and_skips_execution` (:163), `test_the_arguments_a_guard_sees_are_read_only` (:203), `test_a_nested_mutation_does_not_reach_the_call` (:213), `test_approval_lets_the_call_through_on_resume` (:287), `test_a_guard_may_still_block_an_approved_call` (:316), `test_a_failure_message_is_screened_before_the_model_sees_it` (:509), `test_a_failure_is_not_turned_into_a_success` (:544), `test_a_misspelled_tools_name_warns_after_the_unmatched_call` (:379). `tests/guardrails/test_input_guardrail.py` :96–330 (runs once across tool loop :178, multimodal prompt handling :241–260).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'GuardrailResult evaluate_all ApprovalRequired tool_call_approved'`

## Verdict
**Adopt** the five-action vocabulary + construction-time legality matrix wholesale — it generalizes to any inspection boundary. **Adopt** deepcopy+proxy guard input and flag-gated approval resume. **Adapt** the span helper names to your tracer.
