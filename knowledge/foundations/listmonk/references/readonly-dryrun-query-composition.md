<!-- capsule-v2 -->
# readonly-dryrun-query-composition — How are bulk-by-query operations (delete/blocklist/export by arbitrary filter) made safe before execution?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What is the exact dry-run/compose/execute protocol for `%query%`-templated statements?

## Dry-run then splice composition
**Path/Symbol:** `models/queries.go:compileSubscriberQueryTpl` (:148-171) and `Queries.ExecSubQueryTpl` (:173-192); consumers `internal/core/subscribers.go:BlocklistSubscribersByQuery` (:487-497), `DeleteSubscribersByQuery` (:511-521).
**Signature:** `func (q *Queries) ExecSubQueryTpl(searchStr, queryExp string, baseQueryTpl string, listIDs []int, db *sqlx.DB, subStatus string, args ...any) error`.
**Data Shape:** `query-subscribers-template` produces a SELECT whose first bind parameter is a boolean "dry run" flag; every destructive base template embeds that filtered select via another `%query%` placeholder.

### Decisive source
```go
// compileSubscriberQueryTpl performs the dry run on a READ ONLY tx:
stmt := strings.ReplaceAll(q.QuerySubscribersTpl, "%query%", cond)
if _, err := tx.Exec(stmt, true, pq.Int64Array{}, subStatus, searchStr); err != nil {
	return "", err
}
// ExecSubQueryTpl splices the validated filter into the destructive query:
stmt := strings.ReplaceAll(baseQueryTpl, "%query%", filterExp)
a := append([]any{false, pq.Array(listIDs), subStatus, searchStr}, args...)
if _, err := db.Exec(stmt, a...); err != nil { return err }
```

**Flow:** user expression → interpolate into filter template → EXEC with `dry_run=true` on a READ ONLY tx (any non-SELECT fails here) → interpolate the validated filter into the destructive template → execute again with `dry_run=false`. `QuerySubscribers` (core/subscribers.go:106-186) follows the same shape but counts first (`getSubscriberCount` :569-602 runs the COUNT variant inside its own READ ONLY tx to both total and re-prove read-only-ness), then selects in a fresh READ ONLY tx.
**Invariant:** The FIRST bound argument of every templated query family is the boolean dry-run flag — porters who reorder binds silently flip semantics. Empty conditions become literal `TRUE`, so "no filter" means "all subscribers", which is why these endpoints are gated behind explicit permissions (`subscribers:manage`).
**Probe:** `bash -c "cd <repo> && grep -c '%query%' queries/subscribers.sql"` → 9 placeholders; `grep -n 'append(\[\]any{false,' models/queries.go | wc -l` → 1 (the live-execution site; dry run passes literal `true` inline).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "ExecSubQueryTpl", limit: 10 });
```
## Verdict
Adopt the two-phase dry-run protocol (validate on READ ONLY tx, then execute) for any "bulk mutate by saved query" feature. Adapt the boolean-first bind convention to named parameters in your stack. Omit the pq-specific `pq.Array` adapters.
