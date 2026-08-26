<!-- capsule-v2 -->
# update-with-lists-permitted-scoping — How does a privileged actor safely change another user's list subscriptions without privilege escalation?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** How are permitted-list boundaries enforced inside the combined subscriber+lists update?

## Permitted-list scoped replace/merge
**Path/Symbol:** `internal/core/subscribers.go:UpdateSubscriberWithLists` (:396-459); SQL `queries/subscribers.sql -- name: update-subscriber-with-lists` (:160-200); public resubscribe caller `cmd/public.go:processSubForm` (:726-808).
**Signature:** `func (c *Core) UpdateSubscriberWithLists(id int, sub models.Subscriber, listIDs []int, listUUIDs []string, preconfirm, deleteLists, assertOptin bool, permittedListIDs []int, allowResubscribe bool) (models.Subscriber, bool, error)`.
**Data Shape:** `deleteLists=false` = merge (upsert given lists, keep others); `true` = replace (delete unlisted subscriptions first). Field updates are conditional: empty email/name/status/attribs leave old values (`CASE WHEN $2 != '' THEN $2 ELSE email END`).

### Decisive source
```sql
d AS (
	DELETE FROM subscriber_lists WHERE $9 = TRUE AND subscriber_id = $1
		AND list_id != ALL(SELECT id FROM listIDs)
		AND (CARDINALITY($10::INT[]) = 0 OR list_id = ANY($10::INT[]))
)
INSERT INTO subscriber_lists (subscriber_id, list_id, status) ...
	ON CONFLICT (subscriber_id, list_id) DO UPDATE ...
```

**Flow:** conditional field UPDATE → resolve requested lists (IDs xor UUIDs) → optionally DELETE out-of-set subscriptions but ONLY within the permitted set (`$10`; empty permitted set = no scoping, admin path) → upsert requested subscriptions with `preconfirm`-derived status → refetch → optional optin mail (same gate/assert contract as InsertSubscriber). Public subscribe path (`processSubForm`): insert returns 409 → fetch by email → call this with `deleteLists=false, permittedListIDs=nil, allowResubscribe=true` so a returning subscriber re-adds themselves without touching others.
**Invariant:** The permitted-ID guard wraps BOTH the delete arm and the insert arm — a porter who scopes only deletes lets a limited user add subscriptions to arbitrary lists; one who scopes only inserts lets them strip subscriptions via replace-mode. `allowResubscribe` exists because previously-unsubscribed statuses must be flippable by the owner herself.
**Probe:** `bash -c "cd <repo> && grep -cF 'CARDINALITY(\$10::INT[]) = 0 OR list_id = ANY(\$10::INT[])' queries/subscribers.sql"` → 1; `grep -cF 'allowResubscribe' internal/core/subscribers.go` → 2 (signature + pass-through).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "UpdateSubscriberWithLists permittedListIDs", limit: 10 });
```
## Verdict
Adopt the symmetric permitted-set scoping around merge/replace subscription updates. Adapt the CASE-based partial update to your ORM's dirty-field handling. Omit the UUID/ID dual resolution if your IDs are globally public.
