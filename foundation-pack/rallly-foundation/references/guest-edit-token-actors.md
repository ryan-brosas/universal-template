<!-- capsule-v2 -->
# Guest edit-token actors — how do anonymous participants keep editing their own responses?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How is authorization resolved when the actor may be a session user OR an anonymous guest holding a token — without letting a token escalate to admin?

## resolveActor ladder + admin-vs-token separation
**Path/Symbol:** `apps/web/src/trpc/routers/polls/utils.ts:resolveActor/tryResolveActor/tryResolveUserId/createParticipantEditToken` (lines 1–70); consumer boundary `apps/web/src/trpc/routers/polls/participants.ts:list` (lines 167–175) and `canModifyParticipant` (lines 46–69).
**Signature:** `resolveActor(token: string | undefined, ctxUser: {id;isGuest} | undefined): Promise<{id; isGuest}>`; `createParticipantEditToken(userId): Promise<string>` with `ttl: 0 // basically forever`.
**Data Shape:** token payload `{ userId }`, signed session-style (createToken/decryptToken from `@/lib/session`); Actor = `{ id, isGuest }`.

### Decisive source
```ts
// Admin check is intentionally bound to ctx.user only — an edit
// token must never unlock the admin view of other participants.
const isAdmin = ctx.user ? await hasPollAdminAccess(pollId, ctx.user.id) : false;
// Fall back to the edit token so a guest can still see their own
// response when opening the email link in a fresh browser.
const viewerId = isAdmin ? null : await tryResolveUserId(token, ctx.user);
```
```ts
export async function tryResolveActor(token, ctxUser): Promise<Actor | null> {
  const userIdFromToken = await getUserIdFromToken(token);
  if (userIdFromToken) return { id: userIdFromToken, isGuest: true };  // token ⇒ guest for analytics
  if (ctxUser) return { id: ctxUser.id, isGuest: ctxUser.isGuest };
  return null;
}
```

**Flow:** mutations (`delete`/`rename`/`update`) call resolveActor → UNAUTHORIZED if neither token nor session; ownership = participant.userId === actor.id, else poll-admin check. Reads use the finer split: admin from SESSION ONLY; token resolves only the viewer's own row visibility (own note, own identity under hideParticipants). Tokens are issued to logged-in users too on add (confirmation email carries an edit link), but token-derived actors are always analytics-guests because tokens only ever get issued around guest flows.
**Invariant:** token authority ⊂ session authority — a token can never flip isAdmin, never manage others' rows, and never unlock another participant's note. TTL=0 means "no expiry": the email link in a guest's inbox must work indefinitely.
**Probe:** deterministic grep anchors: `grep -n 'must never unlock the admin view' apps/web/src/trpc/routers/polls/participants.ts` → line 168; `grep -n 'ttl: 0' apps/web/src/trpc/routers/polls/utils.ts` → line 21.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "resolveActor tryResolveUserId createParticipantEditToken", limit: 5 });
```

## Verdict
Adopt the actor-resolution precedence and the token-never-elevates boundary verbatim; adapt the signed-token impl (any HMAC/JWT with {userId}); omit PostHog guest semantics if you have no analytics split.
