<!-- capsule-v2 -->
# Single validation gate with an error tuple — how does ONE pre-write function serve create/bulk/update/upsert without duplicating policy?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** Where do all link-write requests get validated, how are failures returned, and how does the same gate re-run safely when editing an existing link?

## processLink — the funnel every write passes through
**Path/Symbol:** `apps/web/lib/api/links/process-link.ts:processLink` (28-594); helper `maliciousLinkCheck` (596-614).
**Signature:** `processLink<T>({ payload: NewLinkProps & T, workspace?, userId?, bulk?, skipKeyChecks?, skipExternalIdChecks?, skipFolderChecks?, skipProgramChecks? }): Promise<{ link, error: string, code?: ErrorCodes } | { link: ProcessedLinkProps & T, error: null }>`.
**Data Shape:** NEVER throws domain errors — returns a discriminated tuple keyed on `error: null`; the caller converts `{error, code}` into `DubApiError`. The success payload is the SAME object mutated/normalized in place (polyfill fields deleted at :560-566: `shortLink`, `qrCode`, `keyLength`, `prefix`, all UTMTags).

### Decisive source
```ts
// failure shape — thrown errors would break bulk loops; tuples let callers batch
return { link: payload, error: "Invalid destination URL", code: "unprocessable_entity" };

// missing URL allowed ONLY for the root-domain link (it IS the homepage redirect)
} else if (key !== "_root") {
  return { link: payload, error: "Missing destination URL", code: "bad_request" };
}

// domain defaulting happens INSIDE the gate: caller may omit domain entirely
if (!domain) {
  domain = domains?.find((d) => d.primary)?.slug || "dub.sh";
}

// update path suppresses re-validation of unchanged uniqueness constraints
skipKeyChecks?: boolean;        // only when key doesn't change (editing a link)
skipExternalIdChecks?: boolean; // only when externalId doesn't change
skipFolderChecks?: boolean;     // only for update / upsert links
skipProgramChecks?: boolean;    // only when program already validated

// projectId is FORCED to the caller's workspace — client value never trusted
projectId: workspace?.id || null,
// userId only ADDED if passed (never reassigned on edit — preserves owner)
...(userId && { userId }),
// program links inherit the program's default folder when none given
folderId: folderId || defaultProgramFolderId,
```

**Flow:** URL normalize (`getUrlFromString`+`isValidUrl`) → UTM tags folded INTO the url via `constructURLFromUTMParams` when any UTMTags key present (:102-111) → workspace domains fetched once → domain defaulted to primary → plan ladder (free: `dubLinkSubdomainCheck`+`proFeaturesCheck`+`businessFeaturesCheck`; pro: subdomain+business; :133-164) → A/B needs `trackConversion` (:166-172) → per-domain policy chain: `dub.sh`/`dub.link` (session-exists probe, malicious URL check) → other Dub-owned domains (destination hostname allowlist from `DUB_DOMAINS.allowedHostnames`, no geo/device/AB, subdirectory parent-link workspace check :236-249) → custom domains (must belong to workspace :252-257; free `.link` registered-domain upgrade check :260-276) → key admission (getRandomKey OR `processKey`+`keyChecks`, see key-admission-ladder capsule) → externalId uniqueness per workspace (:305-322, conflict) → bulk-mode split: bulk forbids unhosted custom images (:324-332); single mode validates tagIds/tagNames against workspace (:337-400), folder plan+access via `verifyFolderAccess("folders.links.write")` (:405-437), program membership + partnerId derivation (:440-472), webhooks Business-plan gate + dedupe + validity (:475-506) → storage env guard for proxy images (:510-516) → date parsing via `parseDateTime` for `expiresAt`/`testCompletedAt` (:519-557) → polyfill strip → normalized payload.

**Invariant:** The gate OWNS normalization: after processLink resolves with `error: null`, downstream writers (createLink/updateLink) receive a payload whose `url` already embeds UTMs, whose `domain` is guaranteed owned/allowed, whose `key` passed the admission ladder, and whose `projectId` equals the authenticated workspace — writers must NOT re-derive these. Every skip* flag exists so the UPDATE flow can run the full gate again while exempting constraints that are definitionally unchanged (computed by the route: `link.domain === updated.domain && link.key.toLowerCase() === updated.key?.toLowerCase()`). Bulk mode moves tag/folder/webhook validation OUT of the gate to the route level (checked once per batch, not per item).
**Probe:** direct integration tests `apps/web/tests/links/create-link-error.test.ts:8-96` — four table-driven cases assert exact envelopes through POST /links: domain-not-in-workspace ⇒ 403 `"Domain does not belong to workspace."`; `url:"invalid"` ⇒ 422 `"Invalid destination URL"`; `tagIds:["invalid"]` ⇒ 422 `"Invalid tagIds detected: invalid"`; oversized utm_source ⇒ 422 zod `too_big`. Feature-level pins in `tests/links/create-link.test.ts` (expiration :304, device targeting :337, geo targeting :371, ab testing :556).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "processLink keyChecks processKey", limit: 5 });
// → apps.web.lib.api.links.process-link.processLink @ process-link.ts 28-594
```

## Verdict
Adopt the error-tuple gate for any multi-writer resource API (bulk loops need per-item failures, not exceptions), the skip-flag pattern for update re-validation, server-forced tenancy fields, and primary-domain defaulting. Adapt the plan ladder and per-domain policy tables to your product. Omit Dub-specific domain brands.
