<!-- capsule-v2 -->
# Status-as-data document — how does a CLI answer "what is standing" for both humans and agents without lying about an unreadable provider?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How should a status command report a provider it could not reach, and what does it tell the operator to do next?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/status.py` — `build_status` (:33-50), `_credits` (:119-134), `_blocked` (:139-177), `next_action` (:182-233), `render_next_action` (:236-258); renderer in `core/management/commands/status.py:render` (:43-96).
**Signature:** `build_status() -> dict` with keys `{onboarding, campaigns, totals, credits, blocked, next_action}`; `credits = {"balance": int|None, "error": ErrorType|None}`; `render_next_action(action: dict) -> str`.
**Data Shape:** one read-only document; per-campaign rows carry the six state counts plus `exportable / exportable_with_email / exportable_without_email`.

### Decisive source
```python
def _credits() -> dict:
    """Read the provider balance, reporting *why* it is unknown rather than guessing.
    A balance we could not read is not a balance of zero, and the difference
    decides whether the operator is asked to top up."""
    if not bettercontact.is_configured():
        return {"balance": None, "error": ErrorType.NO_CREDENTIAL}
    try:
        return {"balance": bettercontact.credit_balance(), "error": None}
    except bettercontact.BetterContactUnavailable as exc:
        return {"balance": None, "error": exc.error_type, "detail": str(exc)}
```

**Flow:** build_status reads only (never raises on a dead provider) → blocked list assembled in the stable ErrorType vocabulary → next_action chosen by arithmetic ordering: onboarding first, then the credit ask *only when* `ranked_for_lookup > 0`, then print-leads (`openoutreach find 0 > leads.csv`), else find-leads. The run-end of `find` renders the *same* derived action — "The end of a run renders this; it does not recompute it" (two earlier attempts put a balance HTTP call inside job.py/lookup.py, giving the bounded-goal loop a payment call and forcing module-level mutable state).
**Invariant:** Unknown ≠ zero: a rejected key or unreachable provider reports *why* it is unknown instead of falling back to 0. Never-before-value: an empty pipeline at zero credits is asked for no money — `ranked_for_lookup > 0` **is** proof value exists (ranked leads already carry written reasons). The credit ask carries the count and the attributed SIGNUP_URL ("every path we show goes through the one URL that applies it"). Command output contract: summary/result to stdout, logs to stderr; `--json` prints exactly one object so it pipes into `jq`; SQLite WAL lets status answer while a job holds the write lock.
**Probe:** `tests/test_status.py` (:51-208) — `test_counts_the_deliverable_the_way_the_export_writes_it` (:51-62, exportable == len(lead_records)), `test_a_rejected_key_is_not_a_balance_of_zero` (:86-93), `test_nothing_is_asked_of_a_run_that_has_qualified_nobody` (:136-142), `test_json_is_one_object_and_nothing_else` (:187-196), `test_credit_ask_carries_the_count_and_the_attributed_url` (:161-171).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "build_status credits blocked next_action", limit: 10 });
```

## Verdict
Adopt: status as one pure dict with separate human/JSON projections; typed unknown-vs-zero credit semantics; blocked reasons named from the same error vocabulary the jobs raise; next-action as ordered arithmetic that never asks for money before value exists, rendered once and reused at run end. Adapt counts to your pipeline states; omit Django/WAL details.
