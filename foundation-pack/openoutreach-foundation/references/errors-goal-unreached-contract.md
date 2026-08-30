<!-- capsule-v2 -->
# Stable error vocabulary & GOAL_UNREACHED — how does a CLI answer agents, operators, and the funnel with one string set?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** What is the error contract for a tool whose primary caller is another program, and what must a "stopped short" message contain?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/errors.py:ErrorType` (:16-51), `format_error` (:53-55), `OpenOutreachError` (:58-69); consumed by `core/job.py:_why_idle` (:241-253) and `cycle.pipeline_summary` (:158-195).
**Signature:** `format_error(error_type, message) -> "error: <type>: <message>"`; `OpenOutreachError(error_type, message)`.
**Data Shape:** stable strings — no_credential / provider_auth / provider_out_of_credits / provider_rate_limited / provider_unavailable / bad_config / onboarding_incomplete / not_initialized / goal_unreached.

### Decisive source
```python
# The rule these exist to enforce is that **nothing may be reported as an empty result**.
# A throttled or unauthorised run that says *"no leads found for your product"* is the
# worst failure this product can have, because the reader concludes the tool does not
# work and nobody reports it.

GOAL_UNREACHED = "goal_unreached"
# Exit 0 means *I got what you asked for* and nothing else, which is the property that
# lets a caller branch without parsing.

class OpenOutreachError(Exception):
    """Deliberately **not** a CommandError: Django catches that one and prefixes it
    with the exception's class name, which would put noise in front of the line an
    agent parses."""
```

**Flow:** providers type refusals at the HTTP boundary (401→provider_auth, 402→provider_out_of_credits, RetryError→provider_rate_limited) → job maps ModelHTTPError→bad_config and BetterContactUnavailable→its own error_type → idle stop composes `{produced} of {goal} — nothing left to do right now.` + pipeline_summary naming WHICH gate holds (no finder key vs addresses-not-requested).
**Invariant:** Values may be added to but never renamed (CLI contract). Exit code carries only met/not-met; everything else lives in the typed line + `--json` `{"error": {type, message}}` on stderr so programs never parse prose. A drained index and three addresses on order are a dead end and a reason to re-run in an hour — "7 of 10" alone cannot tell them apart, so every shortfall names its holding gate.
**Probe:** `tests/test_cycle.py::TestPriority`-adjacent summary coverage (`test_a_keyless_run_says_discovery_stopped_too_not_just_the_lookup` :345-355, `test_nothing_to_do_says_what_it_is_waiting_on` :328-338), `tests/test_output_contract.py` (error-line rendering), `tests/test_job.py::TestStoppingShort` (:179+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "format_error", limit: 5 });
```

## Verdict
Adopt: one add-only vocabulary serving operator/agent/funnel; refusal typing at the boundary where status codes live; exit-code minimalism with typed stderr lines; mandatory gate-naming on any short-of-goal stop. Adapt the vocabulary strings to your CLI; omit Django CommandError commentary if you have no framework error wrapper.
