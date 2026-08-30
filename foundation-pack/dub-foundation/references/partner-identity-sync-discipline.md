<!-- capsule-v2 -->
# Partner identity sync — how do you sync user↔partner profile fields without clobbering or orphaning shared images?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When a user account and its partner mirror share name/image/email, what write discipline prevents conflicts and storage leaks?

## sync-partner-identity: conflict-first availability check, copy-on-sync images, undefined-vs-null update semantics
**Path/Symbol:** `apps/web/lib/partners/sync-partner-identity.ts` (:1-180).
**Signature:** `assertEmailAvailableForIdentitySync({ newEmail, userId, partnerId })`; `syncNameAndImageToPartner({ partnerId, name?, image? })`; `syncNameAndImageToUser({...})`; `isImageReferencedByPartner({ partnerId, imageUrl })`; `requestSyncedEmailChange({...})`.
**Data Shape:** image keys `partners/<id>/image_<nanoid7>` and `avatars/<userId>_<nanoid7>`; both User and Partner tables have unique emails.

### Decisive source
```ts
const [userWithEmail, partnerWithEmail] = await Promise.all([
  prisma.user.findUnique({ where: { email: newEmail } }),
  prisma.partner.findUnique({ where: { email: newEmail } }),
]);
if (userWithEmail && userWithEmail.id !== userId)
  throw new DubApiError({ code: "conflict", message: "Email is already in use." });
if (partnerWithEmail && partnerWithEmail.id !== partnerId)
  throw new DubApiError({ code: "conflict",
    message: `... Do you want to merge your partner accounts instead? (https://d.to/merge-partners)` });
// ...
const hasNameUpdate = name !== undefined;
const hasImageUpdate = image !== undefined;
if (!hasNameUpdate && !hasImageUpdate) return;   // no-op unless explicitly provided
```
(:16-39 dual-tenant conflict; :81-86 undefined gate)

**Flow:** email changes run the CONFLICT check across BOTH namespaces first, and the partner-side conflict message routes users to the merge flow (the merge workflow this lane mined) · image sync always COPIES into per-owner storage keys (never shares one URL across user+partner) so either side's later delete can't orphan the other — `isImageReferencedByPartner` exists for callers that need a reference check before deleting an avatar blob · updates distinguish `undefined` (leave alone) from `null` (explicit clear): `{...(hasNameUpdate && name && { name })}` also skips EMPTY-string names.
**Invariant:** (1) cross-namespace uniqueness must be checked BEFORE any write since two tables enforce it independently — a naive single-table check lets user/partner emails diverge; (2) copy-in semantics make every image write idempotent-safe and deletion locally-scoped; (3) partial-update helpers treat "field absent" as "don't touch", never as "clear" — porting this as a spread of raw nullable fields would wipe profiles on partial PATCHes; (4) email change goes through the verification-email flow (`requestSyncedEmailChange` with `syncIdentity: true`), never a direct write.
**Probe:** deterministic probe: `grep -c 'undefined' apps/web/lib/partners/sync-partner-identity.ts` = 4 (type annotations carrying the undefined-vs-null semantics); behavior exercised by profile-update suites (`tests/partners/`). Coverage caveat: no dedicated unit test pins this file.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "assertEmailAvailableForIdentitySync", limit: 5 });
// → dub.apps.web.lib.partners.sync-partner-identity.assertEmailAvailableForIdentitySync @ sync-partner-identity.ts 7-40
```

## Verdict
Adopt dual-namespace email conflict checks with a merge-flow escape message, copy-on-sync image keys, and explicit undefined-vs-null field semantics. Adapt storage layout. Omit dub's redirect targets.
