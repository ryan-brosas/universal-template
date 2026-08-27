<!-- capsule-v2 -->
# Customer avatar compensating media writes — how does a post-response blob upload keep the DB row honest when it fails?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When an API mints a storage URL synchronously but uploads the bytes after the response, what compensations keep the row from pointing at a missing blob, and when is the OLD blob deleted?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/customers/route.ts:POST` (:57-134) · `apps/web/app/(ee)/api/customers/[id]/route.ts:PATCH` (:47-149) · `DELETE` (:152-177) · `apps/web/lib/api/customers/transform-customer.ts:transformCustomer` (:19-29) + `transformCustomerForCommission` (:31-39) · `apps/web/lib/storage.ts:isStored` (:345-347).
**Signature:** `POST/PATCH = withWorkspace(...)`; `finalCustomerAvatar = avatar && !isStored(avatar) ? `${R2_URL}/customers/${id}/avatar_${nanoid(7)}` : avatar`; `isStored(url) = url.startsWith(R2_URL) || url.startsWith(OG_AVATAR_URL)`.
**Data Shape:** Minted R2 key `${R2_URL}/customers/<customerId>/avatar_<nanoid(7)>`; upload opts `{width: 128, height: 128}`; external (non-stored) URLs pass through untouched.

### Decisive source
```ts
// POST — mint BEFORE the row exists, upload AFTER the response:
const finalCustomerAvatar =
  avatar && !isStored(avatar)
    ? `${R2_URL}/customers/${customerId}/avatar_${nanoid(7)}`   // :64-67
    : avatar;
const customer = await prisma.customer.create({ data: { ..., avatar: finalCustomerAvatar } });
if (avatar && !isStored(avatar) && finalCustomerAvatar) {
  waitUntil(                                                    // :85 post-response
    storage.upload({ key: finalCustomerAvatar.replace(`${R2_URL}/`, ""), body: avatar, opts: { width: 128, height: 128 } })
      .catch(async (error) => {
        // if the avatar fails to upload to R2, set the avatar to null in the database
        await prisma.customer.update({ where: { id: customer.id }, data: { avatar: null } });  // :98-105 COMPENSATION
      }),
  );
}
```
```ts
// PATCH — the isStored gate plus change-detection, and old-blob GC ONLY after the new upload succeeds:
const finalCustomerAvatar =
  avatar && avatar !== oldCustomerAvatar && !isStored(avatar)   // :71-74
    ? `${R2_URL}/customers/${customer.id}/avatar_${nanoid(7)}`
    : avatar;
storage.upload({...}).then(() => {
  if (oldCustomerAvatar && isStored(oldCustomerAvatar)) {
    storage.delete({ key: oldCustomerAvatar.replace(`${R2_URL}/`, "") });  // :102-105 success-only GC
  }
}).catch(async (error) => {
  await prisma.customer.update({ where: { id: customer.id }, data: { avatar: null } });  // :113 same compensation
});
// DELETE — GC the stored blob AFTER the row delete (post-commit eventual cleanup):
await prisma.customer.delete({ where: { id: customer.id } });
if (customer.avatar && isStored(customer.avatar)) {
  storage.delete({ key: customer.avatar.replace(`${R2_URL}/`, "") });       // :167-169
}
```
```ts
// transform-customer.ts — name null-repair is SERIALIZATION-side:
name: customer.name || customer.email || generateRandomName(),              // :25 (and :40 in the commission twin)
```
**Flow:** parse body → mint final URL only when the incoming avatar is external AND (PATCH) different from the stored one → write the row with the final URL → respond → `waitUntil` uploads the bytes → on success (PATCH) delete the previous stored blob → on failure set `avatar: null` in the DB. DELETE removes the row first, then GCs the stored blob. Every read path passes through `transformCustomer`, which folds `name || email || generateRandomName()` so a stored-null name never leaks (POST additionally folds at creation, :63).
**Invariant:** The DB row must never reference a blob that does not exist: the upload's `.catch` compensates by nulling the column, because the response already shipped the URL and cannot be recalled. Old-blob deletion is ordered AFTER the replacement upload succeeds (never delete-then-upload), and DELETE-side GC runs after the row delete — eventual cleanup, hard-delete-choreography shape in miniature. The `isStored` gate means externally-hosted avatars are never re-uploaded or GC'd. Null names are repaired at serialization time, not at write time, so every consumer (including the commission serializer) inherits the ladder.
**Probe:** No direct test for this plane (`tests/**/*customer*` = ∅; `avatar` hits in `tests/tracks/*` are request fixtures, not media-plane tests). Deterministic probes executed at pin: mint template at route.ts :66 and [id]/route.ts :73; `avatar: null` compensation exactly once per file (:103 / :113); `waitUntil` usage once per file (+ import); name-fold at transform-customer.ts :25 and :40; `isStored` definition lib/storage.ts :345-347.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "customer avatar R2 upload waitUntil compensation", limit: 10 }); // rank-1 expected: POST/PATCH avatar blocks
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "transformCustomer", direction: "inbound", depth: 1 }); // customers GET/POST/PATCH/DELETE + commission serializers
```

## Verdict
Adopt mint-URL-then-upload-after-response with a `.catch` that nulls the column, success-ordered old-blob GC, and post-row-delete blob cleanup — the trio that keeps a post-response upload honest. Adapt the 128×128 resize and nanoid key layout to your storage economics; keep the `isStored`-style predicate so foreign URLs are never touched. Omit nothing silently: dropping the compensation leaves rows pointing at 404 blobs forever, since the HTTP response cannot be corrected after the fact.
