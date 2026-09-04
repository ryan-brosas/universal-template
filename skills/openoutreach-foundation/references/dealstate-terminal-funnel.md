<!-- capsule-v2 -->
# DealState terminal funnel — how does a queue-as-status row carry its own schedule and never abandon an in-flight paid job?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** Where do the timing, the provider job handle, and the retry state of a per-item workflow live so a crash or restart loses nothing?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/crm/models/deal.py:DealState` (:6-75), `Outcome` (:78-95), `Deal` (:98-147).
**Signature:** `state = CharField(choices=DealState.choices, default=QUALIFIED)`; `not_before = DateTimeField(null=True)`; `lookup_request_id = CharField(default="")`; `lookup_attempt = PositiveSmallIntegerField(default=0)`.
**Data Shape:** six states — QUALIFIED → READY_TO_FIND_EMAIL → FINDING_EMAIL → RESOLVED | NO_EMAIL_BETTERCONTACT; FAILED (+Outcome.WRONG_FIT) is the LLM's own rejection. Composite index `(state, not_before)` is "the cycle's one query"; UniqueConstraint `(lead, campaign)`.

### Decisive source
```python
# "Do not touch this deal before this time" — the only schedule a deal
# carries, and it gates *this row alone*. Written by the one step that
# waits: the lookup poll's backoff (check_lookup).
not_before = models.DateTimeField(null=True, blank=True, db_index=True)
# The in-flight paid lookup: the provider's job handle and how many times
# it has been polled ... so a restart resumes the job from the deal itself
# and a stalled provider can never hold up anything but this lead.
lookup_request_id = models.CharField(max_length=64, blank=True, default="")
lookup_attempt = models.PositiveSmallIntegerField(default=0)
```

**Flow:** QUALIFIED (exportable immediately; address is enrichment, never precondition) → GP rank gate → READY_TO_FIND_EMAIL → `buy_address` parks the deal at FINDING_EMAIL with its job handle → `check_lookup` doubles `not_before` on the same request_id until hit (RESOLVED) or miss (NO_EMAIL_BETTERCONTACT). A free hub-cache hit skips FINDING_EMAIL entirely.
**Invariant:** Every state below RESOLVED is terminal **by design** — the product is a row in a file, not a conversation. A non-terminating provider job is *never* abandoned and never re-deadlined: the deadline that used to revert FINDING_EMAIL → READY_TO_FIND_EMAIL made an outage worse (the deal returned to the pool and bought a *second* job for the same lead). NO_EMAIL is a distinct terminal from FAILED because it means reachability failed while fit succeeded — the ML labeler keeps it as label 1. FAILED+WRONG_FIT is campaign-scoped and is the labeler's only negative; it is a different column from `Lead.disqualified` (permanent, account-level).
**Probe:** `tests/db/test_deals.py::test_no_email_miss_logs_muted_not_failed` (:33-40) + `test_true_failure_still_logs_failed` (:44-49).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "DealState Outcome terminal funnel not_before", limit: 10 });
```

## Verdict
Adopt: state-is-the-queue rows that carry their own `not_before`, job handle, and attempt counter (restart-resumable, no external scheduler); distinct terminals for "provider found nothing" vs "we rejected it"; uncapped same-handle backoff. Adapt the state names to your funnel; omit Django choices/index plumbing.
