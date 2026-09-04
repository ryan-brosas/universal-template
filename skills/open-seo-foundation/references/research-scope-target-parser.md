<!-- capsule-v2 -->
# Research-scope target parser — how do you turn a raw "example.com/blog" style input into a validated research scope before a paid API ever sees it?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** What are the four scopes, the validation ladder, and the post-filter matching rule?

## Scope grammar: parse → validate → match
**Path/Symbol:** `src/shared/researchScope.ts:parseResearchTarget` (:117-180), `urlMatchesResearchTarget` (:212-234), `isValidDomainHost` (:8-15), `RESEARCH_SCOPE_FILTER_SLOTS` (:187-193); consumer `src/server/lib/domainUtils.ts:normalizeDomainInput`.
**Signature:** `function parseResearchTarget(input: string, requestedScope?: ResearchScope): { ok: true; target: ResearchTarget } | { ok: false; message: string }`; `function urlMatchesResearchTarget(url: string, target: ResearchTarget): boolean`.
**Data Shape:** `ResearchTarget = { scope: exact_url|subfolder|domain|subdomains, hostname (www. stripped), urlHostname (www. kept), path ("" for root; casing/encoding preserved, trailing slash/query/fragment stripped), display }`. Defaults: root input ⇒ subdomains, path present ⇒ subfolder.

### Decisive source
```ts
// The charset check rejects hosts like my_site.com that URL() and tldts
// accept but DataForSEO bills and fails with an opaque "Invalid Field".
if (!hostname || !hostname.includes(".") || !/^[a-z\d.-]+$/.test(hostname) || !isValidDomainHost(hostname))
  return { ok: false, message: "Enter a valid domain like example.com" };
// …post-filter for provider rows that cannot be scoped provider-side:
case "subfolder":
  return path === target.path || path.startsWith(`${target.path}/`);
```

**Flow:** trim → synthesize `https://` if no protocol → URL-parse → reject embedded credentials → lowercase host, strip www → charset check AND PSL check (`tldts.parseTld`: not IP, publicSuffix present, ICANN or private) → normalize path → subfolder requires non-root path (explicit scope that doesn't fit ⇒ ERROR, never silently unscoped) → scope consumed downstream as provider-side filters when supported (`RESEARCH_SCOPE_FILTER_SLOTS`: how many of the vendor's 8 filter conditions each scope burns) and as `urlMatchesResearchTarget` post-filter otherwise (subfolder matches `/blog/post`, NOT `/blogging`).
**Invariant:** Validation exists to prevent BILLED vendor failures — fake TLDs (`example.por`) and underscore hosts pass naive URL parsing but come back as opaque charged errors. Query strings and fragments never create separate scopes.
**Probe:** `src/server/features/ai-search/services/brandLookup.test.ts` + `src/shared/researchScope.test.ts` if present — verify via `grep -rn "urlMatchesResearchTarget\|isValidDomainHost" src --include=*.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "parseResearchTarget urlMatchesResearchTarget RESEARCH_SCOPES isValidDomainHost", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-scope grammar + pre-billing validation ladder + path-prefix-with-boundary post-filter for any domain-scoped analytics product. Adapt the PSL library and error copy. Omit filter-slot budgeting if your vendor has unlimited filter conditions.
