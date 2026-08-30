<!-- capsule-v2 -->
# Hierarchical pause scopes — how do you freeze background work for a subtree (space/base/table) with scheduled auto-resume, enforced at claim time?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does an ops "pause this base" flag stop task CLAIMS in SQL without a per-task lookup, and resume automatically at a future timestamp?

## ComputedUpdatePauseRegistry + buildComputedTaskNotPausedCondition
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/pause/ComputedUpdatePauseRegistry.ts` — `pauseScope` upsert (:79–147), `resumeScope` delete (:149–180), `listScopes` (:182–210), metadata batch resolution (:239–330), `buildComputedTaskNotPausedCondition` (:390–427); consumed by outbox claim/reclaim at ComputedUpdateOutbox.ts:974,:995 and post-claim space re-filter :1111–1140.
**Signature:** `pauseScope({scopeType: 'space'|'base'|'table', scopeId, resumeAt?, reason?, actor?})`; `resumeScope(...)`; condition builder `(eb, alias, now, {includeSpaceScope?}) => SQL NOT EXISTS`.
**Data Shape:** Row `{id ('cup'+16), scope_type, scope_id, paused_at, paused_by, resume_at NULL=suspended-indefinitely, reason, updated_at/by}` unique on `(scope_type, scope_id)`.

### Decisive source
```ts
const activeScopeCondition = sql<boolean>`
  (cps."resume_at" is null or cps."resume_at" > ${now})
  and (
    (cps."scope_type" = 'base' and cps."scope_id" = ${sql.ref(`${alias}.base_id`)})
    or (cps."scope_type" = 'table'
        and (cps."scope_id" = ${sql.ref(`${alias}.seed_table_id`)}
             or cps."scope_id" = any(coalesce(${sql.ref(`${alias}.affected_table_ids`)}, ARRAY[]::text[]))))
    ${includeSpaceScope ? sql`or (cps."scope_type" = 'space' and cps."scope_id" = cb."space_id")` : sql``}
  )`;
return eb.not(eb.exists(activeScopes));
```

**Flow:** pause = single upsert on `(scope_type, scope_id)` (re-pausing refreshes timestamps/reason) → claims embed the NOT-EXISTS predicate so paused subtrees are never even selected (`reason: 'paused'` is a claim-skip reason) → space-level checks need a join to `base.space_id`, so after claiming, rows whose resolved space got paused are filtered again in code (:1111–1140) → resume = DELETE by key returning id (boolean tells caller whether anything was actually active) → `listScopes(activeOnly)` treats `resume_at > now` as still-paused, giving scheduled auto-resume for free. Display metadata (names of scope/space) resolves via one batched query per scope type — never N+1.
**Invariant:** The pause check MUST live inside the claim query (NOT-EXISTS over a tiny table), not application-side filtering after selection — otherwise a hot queue keeps churning paused tasks through claim/lease cycles. Space scope requires the post-claim re-filter because the SQL predicate can only see `base_id` on the row, not the transitive space membership.
**Probe:** No direct spec exists for the registry (coverage caveat). Deterministic evidence: outbox integration specs exercise paused-claim behavior, and devtools layer `ComputedTaskControlLive.pauseScope` (:108–143) drives the same API end-to-end; cite source ranges above as primary evidence.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ComputedUpdatePauseRegistry buildComputedTaskNotPausedCondition pauseScope", limit: 10 });
```

## Verdict
Adopt hierarchical pause scopes with scheduled-resume semantics, claim-time NOT-EXISTS enforcement, upsert-pause/delete-resume state shape, and batched display-metadata resolution; adapt scope types and the affected-tables array column to host schema; omit teable's dual-db (data/meta) resolution if host has one database.
