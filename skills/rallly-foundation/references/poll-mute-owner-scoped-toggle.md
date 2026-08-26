<!-- capsule-v2 -->
# Poll mute owner-scoped toggle — how do you enforce ownership on a boolean flip without a check-then-update race, and what does the client do with the typed result?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** Where is "only the owner can mute this poll" enforced, and how do server, action, and client split the not-found outcome?

## setPollMuted count-scoped updateMany + safe-action + optimistic cache patch
**Path/Symbol:** `apps/web/src/features/poll/mutations.ts:setPollMuted` (lines 156–179); action `apps/web/src/features/poll/actions.ts:setPollMutedAction` (lines 8–31); input `apps/web/src/features/poll/schema.ts:setPollMutedSchema` (lines 34–37); client `apps/web/src/features/poll/components/notification-toggle.tsx` (lines 14–108).
**Signature:** `setPollMuted({ pollId, userId, muted }) → { ok: true } | { ok: false; reason: "notFound" }`.
**Data Shape:** ownership is encoded in the UPDATE's where clause, not a prior find.

### Decisive source
```ts
/**
 * Muting is a per-owner notification preference, so the scope is the owner's
 * userId rather than a space.
 */
export const setPollMuted = async ({ pollId, userId, muted }) => {
  const { count } = await prisma.poll.updateMany({
    where: { id: pollId, userId, deletedAt: null },
    data: { muted },
  });

  if (count === 0) {
    return { ok: false as const, reason: "notFound" as const };
  }

  return { ok: true as const };
};
```
```tsx
queryClient.polls.get.setData({ urlId: input.pollId }, (oldData) => {
  if (!oldData) return oldData;
  return { ...oldData, muted: input.muted };
});
if (input.muted) {
  toast(t("notificationToggleMutedToast", ...), {
    icon: <BellOffIcon className="size-4" />,
    action: { label: t("undo", ...), onClick: () =>
      setPollMuted.execute({ pollId: input.pollId, muted: false }) },
  });
}
```

**Flow:** client toggles → next-safe-action `authActionClient` resolves the caller (`ctx.user.id`, see `safe-action-procedure-ladder`) → mutation writes only where id+userId+not-deleted all match → affected-row count decides the typed outcome (0 rows = wrong owner OR deleted OR missing — deliberately one indistinguishable "notFound") → on ok the client patches the tRPC `polls.get` cache in place and shows an Undo toast that re-executes the same action with the flipped value.
**Invariant:** no read-before-write: the WHERE clause is the authorization check, so a non-owner and a deleted poll are indistinguishable by design (no existence oracle for foreign polls); the guest UI guard (`user?.isGuest || !ownsObject(poll)` → render null) is presentation-only — the server scope is the real gate. Muting is per-OWNER state, not per-space, which is why this rides the user-scoped action surface instead of the space-scoped tRPC router.
**Probe:** direct test `apps/web/src/features/poll/mutations.test.ts:207–239` ("scopes the update to the owner and excludes deleted polls"; "returns notFound when no poll matches the owner scope"). Runner caveat: vitest unavailable in checkout (no node_modules) — assertions read directly at pin.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "setPollMuted updateMany notFound", limit: 5 });
```

## Verdict
Adopt the count-scoped update + single indistinguishable failure reason verbatim; adapt the action transport to your framework; omit the Undo toast if your UX has no undo convention. This is the rare seam in the leaf with a dedicated upstream test suite — keep it green when porting.
