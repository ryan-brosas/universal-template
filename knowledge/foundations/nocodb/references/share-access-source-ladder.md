<!-- capsule-v2 -->
# Share access-source resolution — how do share UUIDs become an access_source, and why must isSharedViewAccess read positively instead of testing is_public?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How is "this request came through a shared VIEW" encoded, and what distinguishes it from a shared BASE?

## Param→source mapping + positive-read gate
**Path/Symbol:** `packages/nocodb/src/helpers/accessSource.ts:resolveShareAccessSource/isSharedViewAccess` (:28–:43, :56–:58 whole file 58L).
**Signature:** `resolveShareAccessSource(params: ShareUuidParams, viewType?: ViewTypes): NcAccessSource | undefined`; `isSharedViewAccess(context): boolean`.
**Data Shape:** `ShareUuidParams {publicDataUuid?, sharedViewUuid?, sharedBaseUuid?, sharedDocUuid?}` → `NcAccessSource.SHARED_FORM | SHARED_VIEW | SHARED_BASE | SHARED_DOC | undefined`.

### Decisive source
```ts
if (params.sharedViewUuid || params.publicDataUuid) {
  return viewType === ViewTypes.FORM
    ? NcAccessSource.SHARED_FORM
    : NcAccessSource.SHARED_VIEW;
}
if (params.sharedBaseUuid) return NcAccessSource.SHARED_BASE;
// ...
export function isSharedViewAccess(context: Pick<NcContext, 'access_source'>) {
  return SHARED_VIEW_ACCESS_SOURCES.includes(context?.access_source);
}
```
(:36–:43, :56–:58)

**Flow:** extract-ids funnels pass resolved params + the SEPARATE `shareViewType` binding here → FORM views refine to SHARED_FORM, everything else stays coarse SHARED_VIEW (`publicDataUuid` is the legacy public-export route and deliberately maps to the view source) → consumers gate exposure rules through `isSharedViewAccess` (notably LTAR related-table restriction) → shared-BASE requests instead authenticate as a pseudo-user via BaseViewStrategy and keep FULL access while still setting `is_public`.
**Invariant:** `is_public === true` ⟺ some share source asserted — enforced per entry point by a unit suite upstream comment ("the invariant test guards that, not a default here"); the read gate MUST be the positive `includes(access_source)` check because a shared base ALSO sets `is_public` but is authenticated with full access — keying exposure rules off `is_public` would leak-constrain shared-base collaborators or, worse, fail OPEN for entry points that forget to stamp access_source (documented in-file).
**Probe:** `cd packages/nocodb && grep -n "isSharedViewAccess\|SHARED_VIEW_ACCESS_SOURCES" src/helpers/accessSource.ts` (:56/:57 single positive-read definition) plus `grep -c "resolveShareAccessSource(" src/middlewares/extract-ids/extract-ids.middleware.ts` (=2 call sites, one per funnel (:445/:1044) — ERRATUM pass 19 audit: shipped probe used `grep -rc` whose count of 3 includes the :33 import line; re-derived to count call sites only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "resolveShareAccessSource isSharedViewAccess NcAccessSource SHARED_VIEW SHARED_BASE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-value source enum + positive-read gate; adapt param names and source values; omit SHARED_DOC if you have no doc-sharing surface. Coverage caveat: the referenced invariant suite lives outside this clone (hiddenFieldMatrix path absent at pin) — recorded as coverage gap, not fabricated as present.
