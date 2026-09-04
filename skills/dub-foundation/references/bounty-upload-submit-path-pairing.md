<!-- capsule-v2 -->
# Bounty upload submit-path pairing — how do you keep a presigned-URL issuer and its submit-time validator honest with each other?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When file uploads go through presigned URLs and the final payload is client-assembled, what makes it impossible to attach someone else's uploaded file to your own submission?

## Connected graph-selected seam
**Path/Symbol:** issuer `apps/web/lib/bounty/api/get-bounty-submission-upload-url.ts` key mint (:141) · validator `apps/web/lib/bounty/api/create-bounty-submission.ts:BountySubmissionHandler.validateFiles` (:413-435) · R2 origin constant `R2_URL` from `@dub/utils` (imported at create-bounty-submission.ts :23) · consumer of validated files: handler step 5 in the nine-step pipeline (:100).
**Signature:** `validateFiles(): void` (private; throws DubApiError unprocessable_entity "Invalid file URL." on any mismatch); issuer returns `{signedUrl, destinationUrl}` where destinationUrl = `${R2_URL}/programs/<programId>/bounties/<bountyId>/submissions/<partnerId>/<nanoid7>`.
**Data Shape:** The shared contract is ONE path template: `programs/{programId}/bounties/{bountyId}/submissions/{partnerId}/…`. Issuer side: exact leaf key with a 7-char nanoid. Validator side: prefix-only check (startsWith) over the pathname, plus an origin equality check against R2.

### Decisive source
```ts
// ISSUER — mints the key from its own context (get-bounty-submission-upload-url.ts :141):
const key = `programs/${programId}/bounties/${bountyId}/submissions/${partnerId}/${nanoid(7)}`;
// destinationUrl handed to the client = `${R2_URL}/${key}` — this is what gets submitted later.
```
```ts
// VALIDATOR — re-derives the expected prefix from ITS OWN context (create-bounty-submission.ts :413-435):
private validateFiles() {
  if (this.files.length === 0) return;
  const r2 = new URL(R2_URL);
  const expectedPath = `/programs/${this.programId}/bounties/${this.bountyId}/submissions/${this.partner.id}/`;
  for (const file of this.files) {
    const parsed = new URL(file.url);
    if (parsed.origin !== r2.origin || !parsed.pathname.startsWith(expectedPath)) {
      throw new DubApiError({ code: "unprocessable_entity", message: "Invalid file URL." });
    }
  }
}
```
**Flow:** admission mints a key under the partner's own subtree and hands back destinationUrl → client uploads bytes to signedUrl, keeps destinationUrl → at finalize the handler (auth context re-derived server-side: programId from the enrollment, bountyId from params, partner.id from the authenticated partner) runs validateFiles as step 5 of the nine-step pipeline, BEFORE requirements/files/social checks persist anything → every stored file URL must be on the R2 origin AND under the prefix derived from the handler's own identity triple.
**Invariant:** (1) Neither side trusts the other's output — the issuer derives the template from the admitted request context, the validator re-derives it from the authenticated submission context; the TEMPLATE is the contract, not any stored or transmitted assertion. (2) The check is prefix-based on the pathname plus origin-equality, so it accepts any leaf name (the nanoid is irrelevant to validation) while rejecting cross-partner paths, cross-bounty paths, cross-program paths, and non-R2 origins in one test. (3) An empty files array passes trivially — the gate only exists when the submission actually carries files (file-less bounties are legal). (4) Because the partner segment comes from the AUTHENTICATED partner id (not the URL), a partner cannot reference another partner's subtree even if they know the nanoid — the nanoid provides no security; the prefix does.
**Probe:** No direct test (grep tests/ for validateFiles/upload pairing = ∅). Deterministic probes executed at pin: expectedPath template at create-bounty-submission.ts :420 byte-matches the issuer key template at get-bounty-submission-upload-url.ts :141 modulo the nanoid leaf and leading slash; `parsed.origin !== r2.origin` :426 + `startsWith(expectedPath)` :427; message "Invalid file URL." :431; NEGATIVE probe: no other site in lib/bounty validates file URLs (single validator); validateFiles is invoked exactly once, at pipeline position 5 (:100).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "validateFiles Invalid file URL R2 programs bounties submissions", limit: 10 }); // rank-1 expected: create-bounty-submission.ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "programs bounties submissions nanoid key getSignedUploadUrl", limit: 10 }); // expected: get-bounty-submission-upload-url.ts :141
```

## Verdict
Adopt the dual-derivation pattern for any presigned-upload flow whose final payload is client-assembled: the mint side pins the object under an actor-scoped path template, and the consume side re-derives the SAME template from its own authenticated context and prefix-checks — never trust a flag, token, or stored assertion that the URL was "issued". Adapt prefix+origin checking (not full-key equality) when the leaf name is random and irrelevant to authorization. Omit nothing silently: validating only the origin lets partners attach each other's files; trusting the issuer's response shape lets a compromised or replayed client submit arbitrary URLs.
