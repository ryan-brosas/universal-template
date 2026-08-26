<!-- capsule-v2 -->
# Share-key URL rewriting — how does one Express mount serve both `/api/docs/:docId/*` and unauthenticated share links without duplicating routes?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do share (`/api/s/...`) URLs reach normal doc routes, and how is access then constrained?

## Prefix rewrite middleware maps /api/s/<key>… onto /api/docs/<SHARE_KEY_PREFIX><key>…; per-endpoint gates re-check share provenance
**Path/Symbol:** `app/server/lib/DocApi.ts:addEndpoints` rewrite (:163–168), form gate `_assertIsPublishedForm` (:1590–1623), form route share branch (:1398–1417); prefix source `SHARE_KEY_PREFIX` from `app/common/gristUrls`.
**Signature:** middleware: `(req, res, next) => { if (req.url.startsWith("/api/s/")) { req.url = req.url.replace("/api/s/", `/api/docs/${SHARE_KEY_PREFIX}`); } next(); }`.
**Data Shape:** share docIds therefore look like `<prefix><key>` when they hit `getDocScope`/`getOrSetDocAuth`, which resolve them through the same home-DB path as regular urlIds. Form sections add `_grist_Views_section.shareOptions = {form?, publish?}` JSON and `_grist_Shares.linkId`.

### Decisive source
```ts
this._app.use((req, res, next) => {
    if (req.url.startsWith("/api/s/")) {
      req.url = req.url.replace("/api/s/", `/api/docs/${SHARE_KEY_PREFIX}`);
    }
    next();
});
// ...inside GET /forms/:vsId:
const linkId = getDocSessionShare(docSession);
if (linkId) {
    /* If accessed via a-share, check the form IS published and the share key
       is associated with THIS form before granting access. */
    this._assertIsPublishedForm({ docData: activeDoc.docData, linkId, sectionId });
}
// _assertIsPublishedForm ladder: section exists → sectionShareOptions.form →
// page found by viewRef → page.shareRef resolves → share.linkId === linkId →
// BOTH publish flags set, else 404 {code:"FormNotFound"} / {code:"FormNotPublished"}
```
**Flow:** every request passes through the rewrite first (mounted before OAuth middleware and routes) → downstream code sees an ordinary doc-scoped URL whose docId encodes the share key → authorization proceeds normally, BUT endpoints that expose extra surface through shares call `getDocSessionShare` and apply an additional provenance gate (the published-form ladder) that anonymous share traffic cannot otherwise satisfy.
**Invariant:** rewriting is purely syntactic — it grants NO access by itself; each shareable capability needs its own explicit gate keyed off session share data, failing closed with indistinguishable 404s ("Form not found" vs "not published" differ only in details.code). Order matters: the rewrite MUST precede route registration and auth middleware or scoped routes never see the mapped id.
**Probe:** `test/server/lib/docapi/DocApiForms.ts:294–330` ("returns 200 when the form is published", 404 `FormNotFound`, 404 `FormNotPublished`, share-unpublished variants).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "SHARE_KEY_PREFIX getDocSessionShare assertIsPublishedForm shareOptions", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt prefix-rewriting plus per-capability provenance gates when one router must serve authenticated and link-shared traffic. Adapt the prefix/key encoding to your URL scheme. Omit the form-specific metatable ladder unless porting forms themselves — but keep the fail-closed 404 uniformity.
