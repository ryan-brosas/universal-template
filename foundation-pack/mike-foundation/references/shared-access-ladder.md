<!-- capsule-v2 -->
# Shared-project access ladder — who may read a document once projects can be shared?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do per-row authorization checks stay correct when a doc's project is owned by user A but shared with user B's email — i.e., when scope-by-`user_id` becomes wrong?

## Centralized owner-or-shared-member helpers
**Path/Symbol:** `backend/src/lib/access.ts:30` (`checkProjectAccess`), `:67` (`ensureDocAccess`), `:94` (`ensureReviewAccess`), `:129` (`filterAccessibleDocumentIds`), `:169` (`listAccessibleProjectIds`). Direct test: `backend/src/lib/__tests__/access.test.ts`.
**Signature:** `checkProjectAccess(projectId, userId, userEmail, db) -> ProjectAccess` (`{ok:true,isOwner,project}` | `{ok:false}`).
**Data Shape:** `projects.shared_with` is a nullable text[] of emails; reviews carry their own optional `shared_with` plus optional `project_id`; every helper takes the caller's `userEmail` alongside `userId`.

### Decisive source
```ts
if (proj.user_id === userId) return { ok: true, isOwner: true, project: proj };
const email = (userEmail ?? "").trim().toLowerCase();
if (email && sharedWith.some((e) => (e ?? "").toLowerCase() === email)) {
    return { ok: true, isOwner: false, project: proj };
}
return { ok: false };
```

**Flow:** ensureDocAccess = doc-owner fast path → if no `project_id`, deny → else project check but with `isOwner:false` FORCED (doc access through sharing never grants ownership). ensureReviewAccess adds a middle rung: direct per-review share list BEFORE falling through to the project check, so standalone reviews (`project_id null`) remain shareable.
**Invariant:** `isOwner` must come from the identity comparison only and be returned separately — delete/rename/member-management gate on it while shared members get read/edit. Email comparisons are trimmed+lowercased on BOTH sides; `listAccessibleProjectIds` queries shares with Postgres containment `cs '["email"]'` and `.neq("user_id", userId)` so own projects aren't double-counted via their own share rows.
**Probe:** `grep -c 'it(' src/lib/__tests__/access.test.ts` → 7 incl "allows shared project access case-insensitively", "allows direct review sharing without project access", "filters user-supplied document IDs to accessible documents".

## Anti-IDOR mass assignment
**Flow:** any route accepting document IDs from a request body MUST pass them through `filterAccessibleDocumentIds` first — it batch-fetches `{id,user_id,project_id}` for the submitted ids, computes `listAccessibleProjectIds` once into a Set, and keeps only owner-owned or reachable-via-shared-project docs. Without it, a caller with access to ANY review could attach arbitrary UUIDs and make `/generate` extract other users' bytes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "checkProjectAccess filterAccessibleDocumentIds shared_with", limit: 10 });
```

## Verdict
Adopt the ladder order (owner → direct list → project membership) and separate `isOwner` flag as portable contracts; adapt the share-list storage (text[] vs join table) and email normalization to your auth; omit Supabase builder specifics.
