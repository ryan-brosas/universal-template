<!-- capsule-v2 -->
# bounce-threshold-action-ladder — Where does a recorded bounce turn into blocklist/unsubscribe/delete, and who decides?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What is the exact record-time escalation contract across provider webhook → core → SQL?

## Config-driven single-statement ladder
**Path/Symbol:** `internal/core/bounces.go:RecordBounce` (:60-88); SQL `queries/bounces.sql -- name: record-bounce` (:1-31); admin settings surface `cmd/settings.go` BounceActions; threshold semantics `$8` count, `$9` action enum.
**Signature:** `RecordBounce(b models.Bounce) error` reads `c.consts.BounceActions[b.Type]` → `{Count int, Action string}` passed as binds $8/$9.
**Data Shape:** types hard|soft|complaint each carry their own (count, action); actions: blocklist | unsubscribe | delete.

### Decisive source
```sql
num AS (
	-- Add a +1 to include the current insertion that is happening.
	SELECT COUNT(*) + 1 AS num FROM bounces WHERE subscriber_id = (SELECT id FROM sub) AND type = $4
),
block1 AS (
	UPDATE subscribers SET status='blocklisted'
	WHERE $9 = 'blocklist' AND (SELECT num FROM num) >= $8 AND id = (SELECT id FROM sub)
		AND (SELECT status FROM sub) != 'blocklisted'
),
bounce AS (
	INSERT INTO bounces (subscriber_id, campaign_id, type, source, meta, created_at)
	SELECT ... WHERE NOT EXISTS (SELECT 1 WHERE (SELECT status FROM sub) = 'blocklisted' OR (SELECT num FROM num) > $8)
)
DELETE FROM subscribers WHERE $9='delete' AND (SELECT num FROM num) >= $8 AND id=(SELECT id FROM sub);
```

**Flow:** resolve subscriber by UUID-or-email → count PRIOR bounces of same type (+1 for this one) → CTEs fire conditionally on the configured action: blocklist updates status (only if not already), unsubscribe twin marks subscriptions unsubscribed, delete removes the subscriber row → bounce row itself inserts ONLY while not blocklisted and count ≤ threshold (post-escalation bounces stop accumulating). Unknown type rejected in Go before SQL. Subscriber-not-found (unique violation on subscriber_id column) is swallowed as success — unknown bouncers must not error webhooks.
**Invariant:** Escalation is ATOMIC with recording (single statement, single round trip) and IDEMPOTENT under retry thanks to the `!= 'blocklisted'` guards and the count>threshold insert suppression. The +1 lives in SQL, not Go — computing the count client-side races concurrent bounces.
**Probe:** `bash -c "cd <repo> && grep -cE \"\\\$9 = '(blocklist|unsubscribe|delete)'\" queries/bounces.sql"` → 0 (actions split across lines: use `grep -c \"\\\$9 =\" queries/bounces.sql` → 3); `grep -cF 'COUNT(*) + 1 AS num' queries/bounces.sql` → 1; `grep -cF 'pqErr.Column == \"subscriber_id\"' internal/core/bounces.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "record-bounce blocklist", limit: 10 });
```
## Verdict
Adopt count-in-SQL atomic escalation with idempotent guards. Adapt action enums to your moderation taxonomy. Omit the specific CTE names.
