<!-- capsule-v2 -->
# Bounty submission upload admission — how do you issue presigned upload URLs that cannot be abused?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When partners upload proof-of-work files for bounties, what admission ladder keeps the object store bounded, per-partner, and cryptographically honest about size and type?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/bounty/api/get-bounty-submission-upload-url.ts:getBountySubmissionUploadUrl` (:38-157) · `apps/web/lib/storage.ts:StorageClient.getSignedUploadUrl` (:143-166) + `getSignedUrl` (aws4fetch `signQuery:true, allHeaders:true`) · entry points `apps/web/lib/actions/partners/upload-bounty-submission-file.ts:uploadBountySubmissionFileAction` (:16-47) and `apps/web/app/(ee)/api/embed/referrals/bounties/[bountyId]/upload/route.ts:POST` (:62-94) · UI consumers `apps/web/ui/partners/bounties/claim-bounty-sheet.tsx` handleUpload (:75-150) + `apps/web/app/(ee)/app.dub.co/embed/referrals/bounties/submission-fields.tsx` handleUpload (:61-100) · `apps/web/lib/upstash/ratelimit.ts:ratelimit` (:5-17, slidingWindow).
**Signature:** `getBountySubmissionUploadUrl({bountyId, fileName, contentType, contentLength, programEnrollment}) => {signedUrl, destinationUrl}`; enrollment is `Pick<ProgramEnrollment,"programId"|"partnerId"|"groupId"|"status"|"createdAt"> & {programPartnerTags: Pick<ProgramPartnerTag,"partnerTagId">[]}`.
**Data Shape:** In: declared file metadata (name/type/byte length) + enrollment row. Out: `{signedUrl}` (single-use PUT transport URL, 600s expiry) + `{destinationUrl}` (`${R2_URL}/programs/<programId>/bounties/<bountyId>/submissions/<partnerId>/<nanoid7>` — the URL that gets stored on the submission later). Constants: MAX_ATTEMPTS=25 / "24 h", CACHE_KEY_PREFIX="bounty:submission:file:upload", MAX_UPLOAD_SIZE_BYTES=5MB, ALLOWED_IMAGE_CONTENT_TYPES = exactly {image/jpeg, image/png, image/webp, image/svg+xml}.

### Decisive source
```ts
// gate order (get-bounty-submission-upload-url.ts :47-138) — rate limit BEFORE the DB lookup:
if (!ACTIVE_ENROLLMENT_STATUSES.includes(status)) throw new DubApiError({ code: "forbidden", ... });
if (!fileName.trim()) throw new DubApiError({ code: "unprocessable_entity", message: "File name is required." });
if (!ALLOWED_IMAGE_CONTENT_TYPES.has(contentType)) throw new DubApiError({ code: "unprocessable_entity", ... });
if (!Number.isInteger(contentLength) || contentLength <= 0 || contentLength > MAX_UPLOAD_SIZE_BYTES) throw ...;
const { success } = await ratelimit(MAX_ATTEMPTS, "24 h").limit(`${CACHE_KEY_PREFIX}:${bountyId}:${partnerId}`);
if (!success) throw new DubApiError({ code: "rate_limit_exceeded", ... });
const bounty = await getBountyOrThrow({ bountyId, programId, include: { ...bountyEligibilityIncludes, program: {...} } });
if (bounty.type === "performance") throw new DubApiError({ code: "forbidden", message: "You are not allowed to submit a performance bounty." });
if (!canPartnerSubmitBounty({ program: bounty.program, bounty, programEnrollment }))
  throw new DubApiError({ code: "not_found", message: "Bounty not found." });   // oracle suppressed for ineligible
const requireImage = !!submissionRequirementsSchema.parse(bounty.submissionRequirements)?.image;
if (!requireImage) throw new DubApiError({ code: "unprocessable_entity", message: "The submission requirements for this bounty do not allow for file uploads." });
// mint (:140-151): key pinned to the partner's own subtree; declared values bound into the signature:
const key = `programs/${programId}/bounties/${bountyId}/submissions/${partnerId}/${nanoid(7)}`;
const signedUrl = await storage.getSignedUploadUrl({ key, contentLength, contentType });
return { signedUrl, destinationUrl: `${R2_URL}/${key}` };
```
```ts
// storage.ts getSignedUploadUrl (:143-166) — the declared headers ARE the signature:
const headers: Record<string> = {};
if (opts.contentLength) headers["Content-Length"] = String(opts.contentLength);
if (opts.contentType)   headers["Content-Type"] = opts.contentType;
return await this.getSignedUrl({ key, method: "PUT", bucket: "public", expiresIn: opts.expiresIn || 600,
  headers: Object.keys(headers).length > 0 ? headers : undefined });
// getSignedUrl signs with aws4fetch { signQuery: true, allHeaders: true } — R2 rejects a PUT whose
// Content-Length/Content-Type differ from the admitted values.
```
**Flow:** partner picks a file in the claim sheet (portal) or embedded submission form → entry point resolves the enrollment (server action: getProgramEnrollmentOrThrow WITH programPartnerTags; embed route: withReferralsEmbedToken context + a SEPARATE programPartnerTag.findMany because the embed auth destructures program/links/partnerGroup out and never includes tags; the embed route also layers its own 60/min-per-token limit under the kernel quota) → kernel runs the seven-gate ladder → mints key + signed PUT URL → client PUTs raw bytes to signedUrl with exactly the admitted Content-Type/Content-Length → on success stores destinationUrl as the file entry (max files = submissionRequirements.image.max ?? BOUNTY_MAX_SUBMISSION_FILES=4) → at finalize time the pass-17 handler pipeline's validateFiles re-checks every stored URL against the same path grammar (see `bounty-upload-submit-path-pairing`).
**Invariant:** (1) The quota is consumed BEFORE the bounty lookup/eligibility checks — an ineligible or missing bounty still burns the caller's own 25/24h sliding-window quota, so abuse self-throttles per (bounty, partner) without ever starving other partners. (2) Admission is declared-value based but enforced twice: the gate checks the client's claims, then the signature binds those exact Content-Length/Content-Type headers so the object store rejects any mismatched PUT — the client cannot upload a different size/type than it was admitted for. (3) Ineligible bounties report not_found, never forbidden — the endpoint leaks no existence information across eligibility boundaries (same posture as the visibility plane). (4) Performance bounties are machine-created only, so they are forbidden at admission too (mirrors the pass-17 creation-pipeline refusal). (5) Uploads are only minted when the bounty's submissionRequirements actually demand an image — the requirement row, not the client, decides whether the plane exists.
**Probe:** No direct test (grep tests/ for getBountySubmissionUploadUrl | uploadBountySubmissionFile = ∅). Deterministic probes executed at pin: MAX_ATTEMPTS=25 :14, CACHE_KEY_PREFIX :15, MAX_UPLOAD_SIZE_BYTES :30; gate line-order census :47→:54→:61→:79(ratelimit)→:91(getBountyOrThrow)→:105(performance)→:112(canSubmit)→:130(requireImage) confirming ratelimit precedes the DB lookup; ALLOWED_IMAGE_CONTENT_TYPES = exactly 4 members :31-36; key template :141; storage allHeaders:true :132 + expiresIn||600 :164; NEGATIVE probe: only two callers of the kernel exist (the server action and the embed route).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getBountySubmissionUploadUrl signed upload url ratelimit", limit: 10 }); // rank-1 expected: get-bounty-submission-upload-url.ts
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "getBountySubmissionUploadUrl", direction: "inbound", depth: 1 }); // expected: server action + embed upload route only
```

## Verdict
Adopt the pre-lookup rate-limit ordering whenever the cheap identity inputs (resource id + actor id) are available before the expensive authorization lookup — it converts abuse into self-throttling at zero cost to legitimate actors. Adopt binding the admitted Content-Length/Content-Type into the presigned signature as the second enforcement layer for any declare-then-upload flow. Adopt not_found-for-ineligible to keep the endpoint existence-oracle-free. Adapt the dual-entry convergence (one kernel, two auth contexts, each supplying the kernel's exact enrollment shape) to your own portal/embed split. Omit nothing silently: moving the rate limit after eligibility lets ineligible callers probe for free; dropping the header binding lets a client admit small and upload large.
