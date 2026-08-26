<!-- capsule-v2 -->
# Cursor identity validation + ext_-aliased fetch — how do you stop a foreign-workspace cursor from leaking rows, and let clients address a resource by THEIR id?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** Beyond buildPaginationQuery's mode selection, what does the list endpoint itself verify about a cursor — and how does single-resource fetch support external identifiers?

## Route-side cursor ownership + getLinkOrThrow alias ladder
**Path/Symbol:** `apps/web/lib/api/links/get-links-for-workspace.ts:48-67` (cursor identity); `apps/web/lib/api/links/get-link-or-throw.ts:getLinkOrThrow` (21-101, esp. 32-56, 79-98).
**Signature:** cursor block runs BEFORE the findMany; `getLinkOrThrow({ workspaceId, linkId?, externalId?, domain?, key? }): Promise<Link & relations>` throwing `DubApiError` on every failure mode with a DISTINCT code.
**Data Shape:** cursors are raw row ids; external ids are client-supplied strings addressed as `ext_<externalId>`.

### Decisive source
```ts
// LIST: a syntactically valid cursor must still belong to THIS workspace
const cursorId = filters.startingAfter || filters.endingBefore;
if (cursorId) {
  const link = await prisma.link.findUnique({ where: { id: cursorId }, select: { id: true, projectId: true } });
  if (!link || link.projectId !== workspaceId) {
    throw new DubApiError({
      code: "unprocessable_entity",
      message: "Invalid cursor: the provided ID does not exist.",
    });
  }
}

// SINGLE FETCH: one loader, three addressing schemes, four distinct errors
if (domain && (!key || key === "")) key = "_root";              // domain-only means root link
const linkId = params.linkId || params.externalId || undefined;
// ext_-prefixed ids translate to the compound unique (projectId, externalId)
...(linkId.startsWith("ext_") && workspaceId
  ? { projectId_externalId: { projectId: workspaceId, externalId: linkId.replace("ext_", "") } }
  : { id: linkId }),

if (!link) {
  if (externalId && !externalId.startsWith("ext_"))
    throw new DubApiError({ code: "bad_request",
      message: "Invalid externalId. Did you forget to prefix it with `ext_`?" });
  throw new DubApiError({ code: "not_found", message: "Link not found." });
}
if (link.projectId !== workspaceId)
  throw new DubApiError({ code: "unauthorized",
    message: `Link does not belong to workspace ${prefixWorkspaceId(workspaceId)}.` });
```

**Flow:** list path: buildPaginationQuery validates MODE → the list fn validates IDENTITY (exists ∧ in-workspace, else one uniform 422 that doesn't distinguish missing vs foreign) → only then the paged query runs. Fetch path: domain-without-key collapses to `_root`; id vs `ext_`-prefixed compound lookup; failures rank bad_request (usage hint) < not_found (existence) < unauthorized (tenancy).
**Invariant:** Cursor pagination leaks data through its SIDE CHANNEL if unvalidated: page contents are workspace-filtered but the cursor itself is an existence oracle and can shift results without an ownership check — dub closes it by resolving the cursor row and asserting tenancy FIRST, returning the same "does not exist" message for both missing and foreign ids (no oracle). The resource loader centralizes the alias grammar (`ext_` prefix = external namespace) so routes never parse ids themselves, and error CODES are chosen so clients can self-correct (bad_request hints at the forgotten prefix). Tenancy mismatch is unauthorized (auth problem), not not_found (existence problem).
**Probe:** direct integration tests `tests/links/list-links.test.ts:163 "Invalid cursor ID ... returns error"` (both directions × invalid id ⇒ exact envelope) and `tests/links/update-link.test.ts:151 "update link using externalId"`; foreign-cursor case is source-grounded (:61 checks projectId) without a dedicated e2e — caveat.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getLinksForWorkspace validateLinksQueryFilters folderIds", limit: 5 }); // list fn
// get-link-or-throw.ts cited directly (check_index_coverage: no_recorded_issue)
```

## Verdict
Adopt pre-query cursor identity resolution with an intentionally uniform error message, and a centralized id-alias loader whose failure codes teach correct usage. Adapt the alias prefix and compound-unique keys. Omit the root-link collapse without homepage links.
