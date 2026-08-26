<!-- capsule-v2 -->
# Two-step paid lookup waterfall — how do you pay for an async provider job without ever resubmitting it?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How should a paid, asynchronous resolve (submit → later poll) be wired so a provider outage cannot turn into a hot resubmit loop, and a stranded deal can never sit invisible forever?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/enrichment/lookup.py:buy_address` (:50-74), `_submit` (:77-123), `check_lookup` (:147-192), `reclaim_lookup` (:126-144), `_back_off` (:214-229).
**Signature:** `buy_address(deal) -> DealState | None`; `check_lookup(deal) -> DealState | None`; `reclaim_lookup(deal) -> DealState`.
**Data Shape:** Deal carries the handle: `lookup_request_id: str`, `lookup_attempt: int`, `not_before: datetime|None`. Returns next state (RESOLVED / NO_EMAIL_BETTERCONTACT / FINDING_EMAIL / READY_TO_FIND_EMAIL) or None = stay put.

### Decisive source
```python
def _delay_for(deal) -> float:
    return min(COLLECT_BACKOFF_BASE_S * (2 ** min(deal.lookup_attempt, 64)),
               COLLECT_BACKOFF_MAX_S)          # BASE=5s, MAX=30 days — uncapped chain

# check_lookup outcome ladder:
if not deal.lookup_request_id: reclaim_lookup(deal)   # no handle → back to buy step
outcome = bettercontact.poll_once(deal.lookup_request_id)
except BetterContactUnavailable: _back_off(deal, advance=False)   # outage ≠ evidence about the job
if outcome.running:              _back_off(deal, advance=True)
# terminated: clear handle; miss → NO_EMAIL_BETTERCONTACT (terminal);
# hit → store email + provider name parts, contribute to hub, → RESOLVED
```

**Flow:** buy: known email → hub cache → paid submit (park at FINDING_EMAIL with request_id, attempt=0, first poll after BASE). poll: running ⇒ double; transient failure ⇒ retry same interval; terminated ⇒ terminal miss or RESOLVED. couldn't-submit ⇒ **stay READY_TO_FIND_EMAIL but write not_before first**, else the row is due again immediately and forever.
**Invariant:** A running job is NEVER abandoned and there is NO deadline — abandoning reverts the deal to buyable, which bought second jobs for already-paid ones (measured: 418 submits / 4,512 polls in a week for ~40 leads during one multi-day provider incident). The interval rails at 30 days only so doubling stays representable (`datetime` OverflowError would strand the deal mid-transition); past that it polls monthly forever. A timeout is evidence about the *provider*, never about whether this person has a findable address. Handle lives on the deal row itself, so restarts survive.
**Probe:** `tests/test_lookup.py::TestCheckLookup` (:144-261), `TestBuyAddress` (:43-137), `TestReclaimLookup` (:268+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "check_lookup", limit: 5 });
```

## Verdict
Adopt: free→paid waterfall with the key check on the paid leg alone; handle-on-the-row persistence; doubling with an interval rail and no attempt cap/deadline; couldn't-submit ⇒ stay-in-state + backoff; reclaim path for handle-less stragglers (two deals were stranded 206h on a live install before this existed). Adapt state names and the hub-contribute hook to your stack; omit BetterContact specifics beyond the shape.
