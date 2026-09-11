<!-- capsule-v2 -->
# Event FK-recovery insert — only the stale attributed-link FK is recoverable; every other 23503 rethrows

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** When an INSERT violates a foreign key, how do you decide which violations to degrade on versus surface?

## POST /api/sdk/v1/event two-arm insert
**Path/Symbol:** `src/routes/sdk.ts:269-330` (primary insert :271-290, FK adjudication :291-329).
**Signature:** `const isLinkFk = insertError?.code === '23503' && String(insertError?.constraint ?? '').includes('attributed_link_id');`
**Data Shape:** Primary insert carries 10 columns incl. last-click stamp (`attributed_link_id`, `attributed_click_id`, `attributed_at` from linkOpenedAt, `session_id`) + sdk identity; fallback insert omits ONLY `attributed_link_id` — the column list must be kept in step by hand (in-code comment :303-304).

### Decisive source
```ts
// sdk.ts:292-299 — narrow recovery predicate:
// Only a stale/unknown *attributed link* FK is recoverable here: record
// the event without link attribution rather than losing it. Any other
// 23503 — e.g. install_id's FK lost to a concurrent install delete — is a
// real error that must surface, not be mislabeled as a link problem.
const isLinkFk =
  insertError?.code === '23503' &&
  String(insertError?.constraint ?? '').includes('attributed_link_id');
```

**Flow:** SDK stamps each in-app event with the deep link that drove it (last-click credit may differ from the install link after re-engagement) → INSERT → on FK failure check BOTH code AND constraint name → link-FK ⇒ warn-log and re-insert WITHOUT link attribution (`attributed_click_id` intentionally kept; null `attributed_link_id` is the correct value for link-keyed aggregation — SIT-261 consumer must not read it as a data bug) → any other 23503 (install deleted mid-request) rethrows to the 500 handler.
**Invariant:** Recovery predicates on DB error codes must match constraint NAME, not just SQLSTATE — broad 23503 handling would swallow real referential corruption as a benign miss; event loss is worse than attribution loss.
**Probe:** `bash -c "grep -cF \"includes('attributed_link_id')\" src/routes/sdk.ts"` → 1 (:298); direct tests `src/routes/sdk.event.test.ts`: it('never loses an event when the attributed link is stale...'), it('rethrows a non-link FK violation (e.g. install deleted mid-request)...'), it('persists the attribution stamp on the in_app_events row').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "23503 attributed_link_id foreign key fallback insert", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt constraint-name-scoped FK recovery for denormalized attribution stamps; adapt which columns the fallback arm keeps; omit if your schema has no optional-reference inserts — but never widen the predicate beyond one constraint name.
