<!-- capsule-v2 -->
# Route-level update choreography — how does PATCH /links/[linkId] reuse the validation gate without re-checking unchanged constraints or leaking cross-workspace moves?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** How do fetch, merge, no-op detection, skip-flag computation, and webhook emission compose into one update route?

## PATCH pipeline over getLinkOrThrow + processLink + updateLink
**Path/Symbol:** `apps/web/app/api/links/[linkId]/route.ts:PATCH` (74-203); loader `apps/web/lib/api/links/get-link-or-throw.ts:getLinkOrThrow` (21-101).
**Signature:** route handler wrapped by `withWorkspace(..., { requiredPermissions: ["links.write"] })`; `getLinkOrThrow({ workspaceId, linkId?, externalId?, domain?, key? })` resolves by id OR `ext_`-prefixed externalId OR domain+key (`_root` implied when key empty).

### Decisive source
```ts
// 1. merge body ONTO the fetched row, restoring NewLinkProps shape
const updatedLink = {
  ...link,
  expiresAt: link.expiresAt instanceof Date ? link.expiresAt.toISOString() : link.expiresAt,
  geo: link.geo as NewLinkProps["geo"],
  ...body,
  // UTM tags passed ONLY when explicitly present — absent tags must preserve existing url params
  ...Object.fromEntries(UTMTags.filter((tag) => tag in body).map((t) => [t, body[t]])),
  // root-domain link may NEVER move domain/key (it IS the domain's homepage)
  ...(link.key === "_root" && { domain: link.domain, key: link.key }),
};

// 2. byte-equal no-op short-circuit returns the STORED link untouched
if (deepEqual(link, updatedLink)) return NextResponse.json(link, { headers });

// 3. tenancy escape hatch is BLOCKED at this route on purpose
if (updatedLink.projectId !== link?.projectId) throw new DubApiError({
  code: "forbidden",
  message: "Transferring links to another workspace is only allowed via the /links/[linkId]/transfer endpoint.",
});

// 4. compute the gate's skip flags from actual diff state
const skipKeyChecks =
  link.domain === updatedLink.domain && link.key.toLowerCase() === updatedLink.key?.toLowerCase();
const skipExternalIdChecks =
  link.externalId?.toLowerCase() === updatedLink.externalId?.toLowerCase();

await processLink({ payload: updatedLink, workspace, skipKeyChecks, skipExternalIdChecks, skipFolderChecks: true });

// 5. writer failure maps to 422 with the raw message; success emits link.updated AFTER response
const response = await updateLink({ oldLink: { domain: link.domain, key: link.key, image: link.image }, updatedLink: processedLink });
waitUntil(sendWorkspaceWebhook({ trigger: "link.updated", workspace, data: linkEventSchema.parse(response) }));
```

**Flow:** `getLinkOrThrow` (workspace-mismatch ⇒ unauthorized; missing ⇒ not_found; un-prefixed externalId ⇒ bad_request hint "Did you forget to prefix it with `ext_`?") → dual folder-access verification (current folder AND target folder, in parallel) → merge → deepEqual early-return → projectId guard → processLink gate → updateLink → waitUntil'd `link.updated` webhook through `linkEventSchema.parse` (schema-validates the outbound envelope). DELETE variant: root-domain links refuse deletion ("You can't delete a custom domain..."), then deleteLink + `link.deleted` webhook. GET variant: folder-scoped read permission check + `transformLink(..., { skipDecodeKey: true })`.
**Invariant:** The route owns DIFF SEMANTICS; the gate stays generic via computed skip flags — key checks rerun only when the address actually changes, externalId checks only when it actually changes, folder checks always skipped (verified at route level instead, against BOTH folders). Absent UTM keys mean "keep current URL params"; present-but-empty means clear. `_root` links are immutable addresses (merge re-pins domain/key). Webhooks fire only on confirmed mutations (post-deepEqual) and parse through the event schema so a bad payload fails loudly rather than poisoning subscribers.
**Probe:** direct integration tests `tests/links/list-links.test.ts` siblings — `tests/links/update-link.test.ts:48 "update link using linkId"`, `:151 "update link using externalId"`, `:327 "update link using PUT"` (PUT=PATCH alias :206), `:205-275` UTM ladder (update-with-url, update-only, same-value idempotence, url-only preserves params, empty-string clears); `tests/links/delete-link.test.ts:38 "cannot delete root link"`; transfer-block message pinned by source :136-142 (no dedicated e2e — caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "processLink keyChecks processKey", limit: 5 }); // gate reuse
// route cited directly: apps/web/app/api/links/[linkId]/route.ts (check_index_coverage: no_recorded_issue)
```

## Verdict
Adopt route-level diff computation feeding a generic gate's skip flags, the deepEqual no-op short-circuit, blocked-tenancy-transfer errors naming the sanctioned endpoint, and schema-validated post-response webhooks. Adapt the permission names and event schema. Omit externalId aliasing if you lack client-side identifiers.
