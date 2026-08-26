<!-- capsule-v2 -->
# Prototype-preserving secret strip — why copy via Object.create instead of `delete`?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does viewMetaGet return a password-less and email-map-less payload without corrupting the loaded (possibly cached) View instance?

## PublicMetasService.viewMetaGet strip block
**Path/Symbol:** `packages/nocodb/src/services/public-metas.service.ts` (:203-221).
**Signature:** `Object.assign(Object.create(Object.getPrototypeOf(view)), view, { password: undefined })` — a shallow copy that keeps the class prototype; then for forms: `publicView.view = { ...publicView.view, email: undefined }` — fresh nested object.
**Data Shape:** Stripped fields: `password` (shared-view auth secret) and, FORM views only, `view.email` (recipient map = which base collaborators get submission emails).

### Decisive source
```ts
// :203-213 (comment quoted verbatim):
// Never leak the stored password to the public viewer. Return a shallow
// copy with password stripped — don't mutate the loaded instance, so the
// strip stays safe even if `View.getByUUID` ever gains caching. Mirrors
// the EE dashboardMetaGet pattern.
const publicView = Object.assign(
  Object.create(Object.getPrototypeOf(view)),
  view,
  {
    password: undefined,
  },
);

// :215-221:
// Form views store an `email` recipient map (which base collaborators get
// submission emails) — builder-only config that must never reach the
// unauthenticated public form. Strip it from the copy (a fresh nested
// object, so the loaded/cached FormView instance is left untouched).
if (publicView.type === ViewTypes.FORM && publicView.view) {
  publicView.view = { ...publicView.view, email: undefined };
}
```

**Flow:** all loading/mutation happens on the live instance (filters/sorts/columns/lock_type are ATTACHED metadata, safe to share) → only at the boundary is a prototype-keeping shallow copy made with secrets shadowed to `undefined` → nested form config replaced by spread-copy before stripping.
**Invariant:** (1) `password: undefined` on a copy still SERIALIZES the key unless the JSON layer drops undefined — the protection is against value leakage in the object graph, not key absence; a porter who "simplifies" to `delete copy.password` mutates the shared instance and poisons every subsequent request when caching lands. (2) The comment encodes forward-compatibility reasoning: correctness must not depend on whether getByUUID caches TODAY. (3) Nested objects need their own copies — spreading the parent does not clone `publicView.view`. (4) Same pattern as EE `dashboardMetaGet` — one idiom across tiers.
**Probe:** Runner blocked at this pin. Deterministic probe: grep confirms exactly one `Object.create(Object.getPrototypeOf(view))` in src/services/public-metas.service.ts and exactly one `email: undefined`; no `delete` statements in the file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "viewMetaGet password undefined", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt copy-with-shadowed-secrets at serialization boundaries of any cacheable entity. Adapt field names. Omit nothing — this is a universal pattern wherever cached instances meet public serializers.
