<!-- capsule-v2 -->
# subscriber-insert-optin-contract — What does creating a subscriber actually do when the email exists or when double opt-in applies?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** How do insert, duplicate-email handling, and opt-in confirmation interact across Go and SQL?

## Insert with upsert-shaped subscription attach
**Path/Symbol:** `internal/core/subscribers.go:InsertSubscriber` (:294-357); SQL `queries/subscribers.sql -- name: insert-subscriber` (:86-112); opt-in hook `Core.consts.SendOptinConfirmation` + `Hooks.SendOptinConfirmation` (`internal/core/core.go:44,54`), invoked at :346-353.
**Signature:** `func (c *Core) InsertSubscriber(sub models.Subscriber, listIDs []int, listUUIDs []string, preconfirm, assertOptin bool) (models.Subscriber, bool, error)` — bool return = "optinSent".
**Data Shape:** Lists may come as IDs OR UUIDs (SQL picks branch on `CARDINALITY($6::INT[]) > 0`). New subscriber status defaults `enabled`; subscription status is `unconfirmed` unless `preconfirm`.

### Decisive source
```go
if pqErr, ok := err.(*pq.Error); ok && pqErr.Constraint == "subscribers_email_key" {
	return models.Subscriber{}, false, echo.NewHTTPError(http.StatusConflict, c.i18n.T("subscribers.emailExists"))
}
...
hasOptin := false
if !preconfirm && c.consts.SendOptinConfirmation {
	num, err := c.h.SendOptinConfirmation(out, listIDs)
	if assertOptin && err != nil { return out, hasOptin, err }
	hasOptin = num > 0
}
```

**Flow:** mint UUIDv4 → INSERT subscriber row → attach to lists with `ON CONFLICT (subscriber_id, list_id) DO UPDATE` where the CASE maps `blocklisted` subscriber status (or blocklisted-at-insert `$4='blocklisted'`) to subscription `unsubscribed` → refetch full subscriber by id-or-email (id empty if the CTE returned nothing) → send double-optin mail only when `!preconfirm && SendOptinConfirmation`; `assertOptin` promotes an optin-mail failure into a hard error (public form path passes true).
**Invariant:** Duplicate email is a DISTINCT outcome (409), not an upsert — the caller decides to resubscribe via `UpdateSubscriberWithLists`. Blocklisting at insert time unsubscribes from ALL touched lists atomically in SQL. Optin mail failure does NOT roll back the insert (mail fires post-commit); only `assertOptin=true` surfaces it.
**Probe:** `bash -c "cd <repo> && grep -cF 'pqErr.Constraint == \"subscribers_email_key\"' internal/core/subscribers.go"` → 1; `grep -cF '!preconfirm && c.consts.SendOptinConfirmation' internal/core/subscribers.go` → 2 (insert + update twins); `grep -c \"4='blocklisted'\" queries/subscribers.sql` → 4.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "InsertSubscriber optin", limit: 10 });
```
## Verdict
Adopt the three-outcome contract (created / 409-exists / optin-pending) and the SQL-side status mapping. Adapt the pq constraint-name sniffing to your driver's unique-violation detection. Omit i18n message keys.
