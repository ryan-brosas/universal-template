<!-- capsule-v2 -->
# Doom-Style Cascading Deletion — how do you delete a resource that spans multiple services, each with its own failure modes?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What orchestration shape makes multi-service deletion (billing + documents + database rows + third-party identity) safe to attempt and honest about partial failure?

## Verify-then-delete ladder with fail-closed rechecks and successor-selection for orphaned resources
**Path/Symbol:** `app/gen-server/lib/Doom.ts` (whole file, 215L) — `deleteOrg` (32–50), `deleteWorkspace` (56–88), `deleteUser` (93–125), `deleteUserFromOrg` (134–157, owner hand-off selection), `_removeBillingFromOrg` (184–214, billing-first detach).
**Signature:** `Doom(dbManager, permitStore, notifier: Pick<INotifier,"deleteUser">, loginSystem, homeApiUrl)`; every public method throws `ApiError` on any incomplete step — nothing fails silently.
**Data Shape:** deletion targets are checked by RE-FETCHING counts after the destructive phase (`finalWorkspaces.length > 0` ⇒ throw); cross-service calls ride `Permit` headers with try/finally `removePermit`.

### Decisive source
```ts
public async deleteWorkspace(workspaceId: number) {
  const workspace = await this._getWorkspace(workspaceId);
  for (const doc of workspace.docs) {
    const permitKey = await this._permitStore.setPermit({ docId: doc.id });
    try {
      const result = await fetch(docApiUrl, { method: "DELETE", headers: { Permit: permitKey } });
      if (result.status !== 200) { throw new ApiError(`failed to delete document ${doc.id}: ...`, 500); }
    } finally { await this._permitStore.removePermit(permitKey); }
  }
  const finalWorkspace = await this._getWorkspace(workspaceId);
  if (finalWorkspace.docs.length > 0) {
    throw new ApiError(`Failed to remove all documents from workspace ${workspaceId}`, 500);
  }
  // There is a window here in which user could put back docs.
  await this._dbManager.deleteWorkspace(scope, workspaceId);
}
// Owner hand-off when deleting a user from a site:
const candidate = sortBy(owners, ["email"])[0];   // owners who are billing managers preferred
await scrubUserFromOrg(orgId, userId, candidate.id, this._dbManager.connection.manager);
```

**Flow:** org deletion = billing detached FIRST (fails loudly if an outstanding Stripe balance exists — never destroy a paying customer's data), then every workspace via the doc-by-doc ladder, then a re-fetch proving zero workspaces remain before the org row goes. Workspace deletion = per-doc DELETE through each document's own API/worker under a scoped permit, then re-fetch proving empty, then remove the workspace row. User deletion = personal-org cascade check → refuse if they still belong to foreign sites → notify/email service → login-system deletion → home DB last. User-from-org deletion never deletes anything: it TRANSFERS ownership to a chosen successor (billing-manager owners preferred, alphabetical tie-break) or refuses with 401 when no owner exists.
**Invariant:** ordering is dependencies-first (external services and children before owning rows), every destructive step is individually verified by a post-condition read (not trusted), and ANY residue aborts with a 500 rather than leaving a half-deleted shell — the caller can retry because completed steps are already gone. Permits are minted per call and revoked in `finally`, so a crashed loop never leaks credentials. The explicit code comment "There is a window here in which user could put back docs" records the accepted race honestly instead of pretending atomicity. A porter who deletes the DB rows first will strand billed accounts; who skips the re-fetch will report success over leftovers.
**Probe:** direct tests live at the integration level: `test/gen-server/lib/scrubUserFromOrg.ts` pins the transfer semantics of `deleteUserFromOrg`'s core, `test/gen-server/lib/removedAt.ts` pins the soft-delete states Doom's rechecks depend on (:1–120); no dedicated Doom unit file exists (coverage caveat — behavior is pinned through those suites plus ApiServer deletion flows).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "Doom deleteOrg deleteWorkspace deleteUserFromOrg scrubUserFromOrg", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the reference choreography for GDPR-style account deletion or any cascading teardown across service boundaries. Adapt the specific services and the successor-selection policy; keep the three invariants — external-dependencies-first ordering, verify-after-delete with hard failure on residue, per-call scoped credentials. Omit the billing-first special case only if you have no paid tier — but then write down why, as grist did in comments.
