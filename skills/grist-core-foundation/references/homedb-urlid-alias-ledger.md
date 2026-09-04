<!-- capsule-v2 -->
# urlId alias ledger — how do stable short doc links survive renames without breaking old URLs?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where do old urlIds go when a doc's urlId changes, and how are conflicts prevented per org type?

## Aliases accumulate per org via ON CONFLICT upsert; creation seeds the shortest free prefix of the docId; every alias is a live cache-invalidation prefix
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: seed loop in `addDocument` (:1747–1759), `_checkForUrlIdConflict` (:3913–3949), rename upsert in `updateDocument` (:1956–1971), `flushSingleDocAuthCache` alias sweep (:1187–1198), `Alias` entity + `MIN_URLID_PREFIX_LENGTH`.
**Signature:** `_checkForUrlIdConflict(manager, org: Organization, urlId: string, docId?: string)`; conflict → `ApiError("urlId already in use", 400)`.
**Data Shape:** `Alias = {urlId, orgId, docId, createdAt}`; uniqueness `(org_id, url_id)`; doc.urlId column mirrors the CURRENT alias (active one).

### Decisive source
```ts
if (!doc.urlId) {
  for (let i = MIN_URLID_PREFIX_LENGTH; i <= doc.id.length; i++) {
    const candidate = doc.id.substr(0, i);
    if (!await manager.findOne(Alias, { where: { urlId: candidate } })) {
      doc.urlId = candidate;
      break;
    }
  }
  if (!doc.urlId) {
    // This should happen only if UUIDs collide.
    throw new Error("Could not find a free identifier for document");
  }
}
```
Rename keeps history:
```ts
// We accumulate old urlIds in order to correctly redirect them...
await manager.createQueryBuilder()
  .insert()
  // if urlId has been used before, update it
  .onConflict(`(org_id, url_id) DO UPDATE SET doc_id = :docId, created_at = ${now(this._dbType)}`)
  .setParameter("docId", doc.id)
  .into(Alias)
  .values({ orgId: doc.workspace.org.id, urlId: props.urlId, doc })
  .execute();
```

**Flow:** create → shortest-free-prefix seed → Alias row. Rename → conflict check EXCLUDING self (`docId` param) → upsert old/new mapping. Lookup: `_doc` CTE unions `docs.id = :urlId` with `aliases.url_id = :urlId` so any historical alias resolves. Cache flush treats EVERY alias as a key prefix (see homedb-docauth-cache-trio). Cross-org move deletes all aliases (see homedb-movedoc-cross-org).
**Invariant:** Conflict scope is org-TYPE dependent — support-org docs check GLOBALLY (examples appear on team sites), personal orgs check across ALL personal orgs (`orgs.owner_id is not null`), team sites check own org PLUS the example org (:3931–3937). Second check forbids a urlId equal to ANY existing docId ("a recipe for confusion and mischief", :3944–3947). A porter who treats aliases as replace-not-accumulate breaks every bookmark issued before a rename.

### Probe (direct tests)
`bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "cannot use an existing docId as a urlId" test/gen-server/lib/urlIds.ts'` → :83.
`bash -c 'grep -c "onConflict" app/gen-server/lib/homedb/HomeDBManager.ts'` → ≥ 3.
Direct tests: `test/gen-server/lib/urlIds.ts` parametrized over personal/team orgs (same-urlId 400s :50, distinct ok :63, example reuse :76, docId-as-urlId :83, reverse reuse :102, disambiguation :113).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"Alias urlId _checkForUrlIdConflict MIN_URLID_PREFIX_LENGTH onConflict","limit":8,"detail":"ids"}'`

**Verdict:** ADOPT — accumulate-and-redirect alias ledgers are the durable pattern; the org-type-dependent conflict grammar is the port trap.
