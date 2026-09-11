<!-- capsule-v2 -->
# DocPrefs dual-plane storage — how do per-user and doc-default preferences coexist under one (doc_id, user_id) key?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where do doc-level defaults vs "just for me" prefs get stored, who may write which, and how are they cached across servers?

## COALESCE-null-user upsert semantics; only owners write docDefaults; pubsub-cached with post-commit invalidation
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `_doGetDocPrefs` (:3644–3660), `setDocPrefs` (:3412–3438, owner gate :3419–3421 + upsert :3429–3433), `getDocPrefsForUsers` (:3443–3454); `Caches.ts` `_docPrefsCache` (:32–37).
**Signature:** `getDocPrefs(scope: DocScope): Promise<FullDocPrefs>` where FullDocPrefs = `{docDefaults: DocPrefs, currentUser: DocPrefs}`; `getDocPrefsForUsers(docId, userIds | "any") => Map<number|null, DocPrefs>`.
**Data Shape:** `doc_pref` rows keyed `(doc_id, user_id nullable)`; user_id NULL = docDefaults. Upsert conflict target `(doc_id, COALESCE(user_id, 0))` because postgres treats NULLs as distinct in unique indexes. Merge is SHALLOW spread: `{...origPrefs.docDefaults, ...newPrefs.docDefaults}`.

### Decisive source
```ts
if (newPrefs.docDefaults) {
  if (doc.access !== roles.OWNER) {
    throw new ApiError("Only document owners may update document prefs", 403);
  }
  const prefs = { ...origPrefs.docDefaults, ...newPrefs.docDefaults };
  updates.push({ docId, userId: null, prefs });
}
if (newPrefs.currentUser) {
  const prefs = { ...origPrefs.currentUser, ...newPrefs.currentUser };
  updates.push({ docId, userId, prefs });
}
await manager.createQueryBuilder()
  .insert().into(DocPref)
  .values(updates)
  .onConflict(`(doc_id, COALESCE(user_id, 0)) DO UPDATE SET prefs = EXCLUDED.prefs`)
  .execute();
```
Read path gates on access first (`_doGetDocPrefs` runs `_verifyAclPermissions` with `accessStyle: "openNoPublic"` — public shares can't read prefs).

**Flow:** read → owner-checked doc fetch → two pref rows folded into FullDocPrefs. Write → same fetch → per-plane merge → batch upsert → `caches?.addInvalidationDocPrefs(notifications, [docId])` AFTER commit. Cross-server coherence rides the redis PubSubCache channel `docPrefsCache:<docId>` (5-min TTL fallback).
**Invariant:** openNoPublic access style exists SOLELY for this path — everyone@-shared docs must not leak prefs to the public. The owner check compares `doc.access !== roles.OWNER` on the FETCHED access (post readonly-downgrade), so billing-frozen owners also lose write rights. A porter using a plain unique index without COALESCE gets duplicate default rows on every save.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "COALESCE" app/gen-server/lib/homedb/HomeDBManager.ts | head -2'` → :3432 (doc prefs) + :1486 (org prefs twin).
`bash -c 'grep -n "should cache docPrefs and refetch when invalidated or expired" test/gen-server/lib/HomeDBCaches.ts'` → :281.
Direct tests: `test/gen-server/lib/HomeDBCaches.ts` :281 + cross-server :318; `test/gen-server/lib/prefs.ts` / `test/gen-server/lib/DocPrefs.ts` suites.

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"setDocPrefs DocPref _doGetDocPrefs getDocPrefsForUsers openNoPublic","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — null-means-default two-plane prefs with COALESCE upserts generalize to any per-entity/per-user settings table.
