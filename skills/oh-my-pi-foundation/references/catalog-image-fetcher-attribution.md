<!-- capsule-v2 -->
# Provider-side image fetchers — how does a blob server attribute a vendor's inbound GET?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When you hand an LLM API an image URL, whose infrastructure fetches it, and how do you recognize them?

## Captured UA registry + corroboration flags + attribution-NOT-auth framing
**Path/Symbol:** `packages/catalog/src/wire/image-fetchers.ts:IMAGE_FETCHERS` (:63), `identifyImageFetcher` (:142), `ImageFetcherMatch.corroborated`.
**Signature:** `identifyImageFetcher(headers: Headers | Record<string, string|string[]|undefined>): ImageFetcherMatch | null`.
**Data Shape:** per identity: `{vendor, label, userAgent: string | RegExp, markerHeaders: readonly string[], observedVia, note?}` — five entries (openai-file-downloader, anthropic-claude-user, anthropic-claude-user-preview, xai-image-api-fetch, google).

### Decisive source
```ts
// NOT an authentication mechanism. Every value here is a request header
// chosen by the caller and is trivially forged. Authorize blob reads with an
// unguessable URL (single-use capability token, short TTL) and treat a
// fetcher match as attribution/telemetry only.

// Always false for identities declaring no markers — absence of
// corroboration is not evidence against the match.
corroborated:
  identity.markerHeaders.length > 0 &&
  identity.markerHeaders.every(header => headerValue(headers, header) !== undefined),
```

**Flow:** inbound request → read User-Agent case-insensitively (Headers instance or raw record with array tolerance) → exact-string match first-class, regex for versioned agents (`Claude-User/\d+`, `XaiImageApiFetch/\d+ `) → match returns identity plus separate corroboration boolean from proprietary marker headers (`openai-internal-smokescreener`, `x-xaifetchid`) → null when nothing matches.
**Invariant:** (1) agent contracts deliberately do not overlap so lookup order carries no meaning; (2) the Anthropic preview entry exists to PREVENT miscounting link prefetches as image fetches; (3) operational quirks live in `note` (OpenAI issues two near-simultaneous GETs per image — duplicates are expected, not replay); (4) generic infra headers corroborate nothing by design.
**Probe:** direct `packages/catalog/test/image-fetchers.test.ts:39` (per-vendor attribution + corroboration), `:54` (missing marker downgrades only corroboration), `:62` (link fetcher vs image fetcher separation), `:69` (version-bump resilience), `:77` (case-insensitive raw headers), `:90` (unknown/absent → null).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "identifyImageFetcher IMAGE_FETCHERS Claude-User", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the registry + corroboration split and the explicit attribution-not-auth contract if you operate blob/image servers behind agent APIs; adapt entries to vendors you actually serve; omit entirely otherwise. Coverage caveat: none.
