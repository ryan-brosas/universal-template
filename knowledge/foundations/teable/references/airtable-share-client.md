<!-- capsule-v2 -->
# Airtable share client — how do you read view configs and rollup sources the official API never exposes?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How is an undocumented share-link endpoint resolved, authenticated, and parsed with flat memory, and what typed failures must each step emit?

## Share-session scraping + token-filtered JSON assembly
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-share.client.ts`:`AirtableShareClient` (:109–382).
**Signature:** `resolveShare(shareLink): Promise<IAirtableShareSession>`; `assertBaseMatch(expectedBaseId): void`; `fetchViewConfig(viewId): Promise<IAirtableViewConfig>`; `fetchApplicationModel(): Promise<Map<string, IAirtableRollupSource>>`.
**Data Shape:** session = `{appId, accessPolicy, requestId, pageLoadId, codeVersion, cookie}` scraped from `window.initData` in the share page HTML; every failure throws `AirtableShareError` with a five-value reason: `not_public | not_a_base | requires_auth | base_mismatch | resolve_failed`.

### Decisive source
```ts
const root = await this.assembleJson(
  Readable.fromWeb(response.body as any),
  /(?:^|\.)(rowOrder|signedUserContentUrls)(?:\.|$)/   // view data call
);
...
const root = await this.assembleJson(
  Readable.fromWeb(response.body as any),
  /(?:^|\.)(tableDatas)(?:\.|$)/                       // application-model call
);
```
with
```ts
/** Assembles the JSON value while dropping the matched (large) payload branches. */
private async assembleJson(stream: Readable, ignoreBranches: RegExp) {
  const tokens = stream.pipe(parser()).pipe(ignore({ filter: ignoreBranches }));
  const assembler = Assembler.connectTo(tokens);
  await finished(tokens);
  return (assembler.current ?? {}) as Record<string, unknown>;
}
```

**Flow:** canonical URL build (`airtable.com/{appId}/{shrId}` — bare shr id 404s) → fetch page with browser UA + manual redirect (redirect to `/login` ⇒ typed `requires_auth`) → scrape requestId/initData (shared VIEW without sharedApplicationId ⇒ `not_a_base`) → replay session verbatim against `/v0.3/view/{id}/readData` and `/v0.3/application/{id}/read` with inter-service headers, cookies, and 200 ms throttle → stream-json assembles responses while DROPPING huge branches at token level (`rowOrder`+`signedUserContentUrls`, `tableDatas`) so memory stays flat regardless of records/base size.
**Invariant:** The endpoint is read-only, authenticated solely by the signed access policy embedded in the share page — no PAT involved. Every failure mode has a typed reason; the client never half-applies: `assertBaseMatch` runs before any model read. Rollup filters are located by SHAPE (an object carrying a `filterSet`) so key renames can't break extraction.
**Probe:** `grep -cF "signedUserContentUrls" apps/nestjs-backend/src/features/airtable-import/airtable-share.client.ts` returns 1; `grep -cF "mayExcludeCellDataForLargeViews" ...` returns 1.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"AirtableShareClient resolveShare assembleJson fetchApplicationModel","limit":5,"detail":"ids"}'
```

## Verdict
Adopt token-level branch dropping for giant JSON APIs and typed-reason session resolution for undocumented endpoints; adapt endpoints/scrape patterns per target; omit Airtable's specific header set. Coverage caveat: none.
