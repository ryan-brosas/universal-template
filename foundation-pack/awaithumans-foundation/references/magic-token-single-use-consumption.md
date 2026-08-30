<!-- capsule-v2 -->
# Magic-Token Single-Use Consumption — replay protection must survive the caller's failure

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** Where exactly is a magic-link token burned, and why does consumption commit independently of task completion?

## Pre-check + PK-conflict INSERT, self-committed before returning
**Path/Symbol:** `packages/python/awaithumans/server/services/email_token_service.py` — module docstring rationale (:1-17), `try_consume_token` (:31-59); table `server/db/models/consumed_email_token.py` (jti primary key).
**Signature:** `async try_consume_token(session: AsyncSession, jti: str) -> bool` — True first-use, False replay.
**Data Shape:** one row per jti; no expiry column — TTL enforcement lives in HMAC verification upstream, this table only remembers redemption FOREVER.

### Decisive source
```python
existing = await session.execute(
    select(ConsumedEmailToken).where(ConsumedEmailToken.jti == jti)
)
if existing.scalar_one_or_none() is not None:
    return False                       # cheap pre-check (in-memory SQLite pools)
session.add(ConsumedEmailToken(jti=jti))
try:
    await session.commit()             # commits ITS OWN row before returning
except IntegrityError:
    await session.rollback()
    return False                       # concurrent loser
return True
```
Docstring: leaving the token reusable on completion failure "opens a window where a flaky DB moment lets an attacker retry"; once consumed, consumed even if completion didn't apply — the human re-engages via dashboard.

**Flow:** email action POST → HMAC verify (upstream, magic-link-action-tokens capsule) → try_consume_token FIRST → True ⇒ complete the task → False ⇒ replay rejected. Two concurrent submissions both INSERT; PK constraint makes exactly one win.
**Invariant:** the consumption write must NOT ride the caller's transaction — downstream `complete_task` failures must not roll the marker back. The pre-select exists only because some SQLite pool configs don't share PK constraints across connections; IntegrityError remains the authoritative race gate.
**Probe:** `packages/python/tests/email/test_email_token_service.py` (`test_first_consume_returns_true`:40, `test_second_consume_returns_false`:45, `test_distinct_jtis_are_independent`:52). Executed behaviorally at pin against in-memory aiosqlite: `True False`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "try_consume_token ConsumedEmailToken IntegrityError", limit: 4 });
```
Live rank-1/2 line-exact (:31-59 function, :28-37 model).

## Verdict
Adopt commit-inside-the-helper and the PK-race-as-authority pattern; adapt the pre-check to your database's real constraint semantics (document WHY it exists like the source does); omit forever-retention only if you add your own replay-window policy consciously.
