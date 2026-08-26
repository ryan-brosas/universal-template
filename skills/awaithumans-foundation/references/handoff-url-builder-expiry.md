<!-- capsule-v2 -->
# Handoff URL Builder & Task-Bound Expiry — one helper so notifier code never thinks about HMACs

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** When should a Slack-visible dashboard link be a SIGNED login handshake vs a plain task URL, and when does the signed one stop working?

## params-or-unsigned dispatch; expiry = the task's own deadline
**Path/Symbol:** `packages/python/awaithumans/server/channels/slack/handoff_url.py` — `_unsigned_url` (:27-28), `build_review_url` (:31-43), `task_handoff_expiry` (:46-52); types twin `handoff_url_types.py` (`HandoffParams` frozen dataclass :13-25, kept separate so importers don't pull in `cryptography`).
**Signature:** `build_review_url(*, task_id: str, params: HandoffParams | None) -> str`; `task_handoff_expiry(timeout_at: datetime) -> int` = `to_utc_unix(timeout_at)`.
**Data Shape:** signed form = `{PUBLIC_URL}/api/auth/slack-handoff?u=<user_id>&t=<task_id>&e=<exp_unix>&s=<sig>` via urlencode; unsigned form = `{PUBLIC_URL}/task?id=<task_id>`.

### Decisive source
```python
def task_handoff_expiry(timeout_at: datetime) -> int:
    """...We bind the URL's expiry to the task's own deadline so a 7-day
    approval still has a working link on day 6. Using `task.timeout_at`
    directly keeps the contract simple: link dies with the task."""
    return to_utc_unix(timeout_at)
```
(to_utc_unix is mandatory here — see naive-datetime trap capsule; `.timestamp()` on the raw DB value would shift by local offset.)

**Flow:** caller has a resolved assignee (user_id + timeout_at) → mint `HandoffParams` → sign_handoff over the pipe-joined triple → urlencode → handoff route. No assignee yet (broadcast pre-claim, or unclaimed-cancel) → pass `params=None` → unsigned URL; password-equipped users still get in, Slack-only users bounce to claim-then-sign.
**Invariant:** the URL's lifetime is DERIVED from the task row, never configured separately — a fixed TTL would either outlive the task (orphan accepted links) or die before a long approval finishes. Signature scheme lives in core/slack_handoff.py (covered by hkdf-handoff-urls capsule); this module is the assembly point.
**Probe:** graph Route nodes pin both shapes: search_graph `build_review_url task_handoff_expiry HandoffParams` rank-1..3 line-exact (:31-43, :46-52, types). Behavioral: expiry equals timeout_at's UTC epoch (see utils-time-naive-utc capsule probe).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "build_review_url task_handoff_expiry HandoffParams", limit: 4 });
```

## Verdict
Adopt the params-None-means-unsigned dispatch and deadline-derived expiry; adapt the query-param names/route path to your auth exchange endpoint; omit the lightweight-types-module split only if your signing import is already cheap.
