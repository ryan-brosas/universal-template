<!-- capsule-v2 -->
# Mention detection — what counts as "the brand was mentioned"?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How is a mention decided from raw answer text so Share-of-Voice numbers mean the same thing across providers?

## Lowercase substring over names + aliases + domains
**Path/Symbol:** `apps/worker/src/jobs/process-prompt.ts:analyzeMentions` (L212–240), `extractDomainFromUrl` (L203–210); report twin in `apps/worker/src/report-worker.ts:analyzeMentions` (L160–192).
**Signature:** `analyzeMentions(content, brand, competitorsList): { brandMentioned: boolean, competitorsMentioned: string[] }`.
**Data Shape:** inputs are lowercased whole; brand set = `[name, ...aliases]` + `[website host, ...additionalDomains]` each www-stripped/lowercased via `extractDomainFromUrl` (prefixes `https://` when missing, falls back to string strip on parse failure). A competitor matches if ANY of its names/aliases OR any of its `domains` is a substring.

### Decisive source
```ts
const contentLower = content.toLowerCase();
const brandNames = [brand.name, ...(brand.aliases || [])].map((n) => n.toLowerCase());
const brandDomains = [extractDomainFromUrl(brand.website), ...(brand.additionalDomains || []).map(extractDomainFromUrl)];
const brandMentioned =
	brandNames.some((n) => contentLower.includes(n)) || brandDomains.some((d) => contentLower.includes(d));
```

**Flow:** applied to `textContent` per run at save time (`brandMentioned`, `competitorsMentioned` columns), so all downstream metrics read precomputed booleans and never re-parse raw output. The onboarding pipeline feeds this exact matcher: aliases containing the canonical name as a substring are dropped (`filterRedundantAliases`) because they would add no discriminating power.
**Invariant:** mention = case-insensitive SUBSTRING, not word-boundary match — deliberate, because model answers mangle casing and punctuation around brand names. The cost is false positives for short/generic alias strings; the mitigation lives upstream in alias curation, not in a cleverer matcher.
**Probe:** no dedicated unit test file — the contract is pinned indirectly by report-metrics tests (which feed hand-built `brandMentioned` rows through SoV math) and by scheduling-under-failure's composition harness. State this caveat when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "analyzeMentions extractDomainFromUrl brandMentioned competitorsMentioned", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the name+alias+domain substring funnel verbatim — it is deliberately dumb so it cannot drift between surfaces; adapt by adding your own alias hygiene (substring-redundant alias filtering is worth porting from onboarding/utils); omit the duplicated report-worker twin only if you can share one module.
