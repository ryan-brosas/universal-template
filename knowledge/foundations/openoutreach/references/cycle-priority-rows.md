<!-- capsule-v2 -->
# Cycle priority rows — what does one unit of work mean when priority must be data?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you express a fixed-priority action hierarchy so that "what ran, in what order, and whether money was spent" is one readable artifact instead of scattered conditionals?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/cycle.py:run_one_action` (:91-143), `ROWS` (:336-341).
**Signature:** `run_one_action(campaign, buy_addresses: bool = False, max_new_lookups: int | None = None) -> bool`.
**Data Shape:** `ROWS: tuple[tuple[name, row_fn, spends], ...]` where `row_fn(campaign) -> bool`; `spends` marks the single money-spending row. Returns True iff some row acted.

### Decisive source
```python
may_spend = buy_addresses and (max_new_lookups is None or max_new_lookups > 0)
for name, row, spends in ROWS:
    if spends and not may_spend:
        ...continue...
    started = time.monotonic()
    acted = row(campaign)
    ...
    if acted:
        return True   # nothing below it runs — this IS the priority
return False
```
```python
ROWS = (
    ("check for the email address we ordered", _check_lookups, False),
    ("rank the qualified leads",               _score_qualified, False),
    ("buy an email address",                   _buy_addresses, True),
    ("find & qualify new leads",               _top_up, False),
)
```

**Flow:** walk rows top→bottom → first row returning True wins and the cycle returns → no row acted ⇒ log a debug pipeline summary and return False → the caller (`job._work_to_goal`) treats False as "nothing can advance".
**Invariant:** Priority is *only* the tuple order — there is no second place it is written down. The paid row is skipped by the `spends` flag + `may_spend`, never by an internal gate inside `_buy_addresses`: free address sources (known email, hub cache) must still run with no key/credits, because a missing key used to switch off the free reads exactly when a free hit was worth most.
**Probe:** `tests/test_cycle.py::TestPriority::test_an_in_flight_lookup_outranks_everything` (:54; also :72/:83/:91 rank each pair) plus `TestBuyingIsOffUnlessAskedFor` (:103-130 — paid row skipped, free rows still run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "run_one_action", limit: 5 });
```

## Verdict
Adopt rows-as-data `(name, fn, costs_money)` + first-True-wins walking + per-row timing logs; adopt spend-opt-in as a per-call parameter defaulting False ("a caller who forgets a flag should lose a feature, never money"). Adapt row names to your domain's operator vocabulary (names describe what happens to the *lead*, not which function ran); omit the Django query machinery behind `_due`/`_apply` (queue-as-status: work found by `Deal.objects.filter(state=...)`, never pre-created rows — port the idea, not the ORM code).
