<!-- capsule-v2 -->
# SearchQuery Mutator — how do you edit GitHub's `q=` parameter without corrupting quoted values, and what implicit queries do bare list URLs carry?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the tokenizer grammar, the implicit-query synthesis, and the keyword-dedup rule?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/search-query.ts:SearchQuery` (whole file, :1–130); consumer `source/helpers/set-status-filter.ts`.
**Signature:** `SearchQuery.from(Location|HTMLAnchorElement|Record<string,string>)`; chainable `.set/.edit/.replace/.remove/.append/.prepend/.includes`; `.href` getter serializes.
**Data Shape:** query lives as `queryParts: string[]` — tokenizer regex `/[^\s"()]+:[^\s"()]*(?:"[^"]*")?|\([^)]*\)|"[^"]*"|[^\s"():]+/g`.

### Decisive source
```ts
// Bare URLs IMPLY hidden qualifiers that an explicit ?q= would override:
const labelName = labelLinkRegex.exec(this.url.pathname)?.groups?.label;  // /owner/repo/labels/x
if (labelName) return this.queryParts = ['state:open', 'label:' + SearchQuery.escapeValue(decodeURIComponent(labelName))];
this.queryParts.push(/\/pulls\/?$/.test(this.url.pathname) ? 'is:pr' : 'is:issue', 'state:open');
if (this.url.pathname === '/issues' || this.url.pathname === '/pulls') {
	this.queryParts.push(this.url.searchParams.has('user') ? 'user:'+get('user') : 'author:@me', 'archived:false');
}
```
```ts
// Keep only the LAST occurrence of a type keyword:
function deduplicateKeywords(array, ...keywords) {
	let wasKeywordFound = false;
	for (const current of array.toReversed()) {
		const isKeyword = keywords.includes(current);
		if (!isKeyword || !wasKeywordFound) { deduplicated.unshift(current); wasKeywordFound ||= isKeyword; }
	}
}
```

**Flow:** construct from anchor/location/params → tokenize existing `q` OR synthesize implied parts (label link → `label:` + `state:open`; `/pulls` → `is:pr state:open`; global lists add `author:@me archived:false`) → edits operate on parts → `.href` re-serializes with a TRAILING SPACE appended (`'q' = get() + ' '`) and rewrites `/labels/x` paths to `/issues` (avoids a redirect that drops the query, #5176).
**Invariant:** the trailing space in serialization is deliberate (keeps GitHub's own UI appends well-formed) — porters "cleaning it up" break subsequent server-side edits. Keyword dedup scans REVERSED and keeps the last `is:issue`/`is:pr`. Quoted values may contain spaces AND colons; the tokenizer handles both, naive `.split(' ')` does not. Label values are URI-decoded once at synthesis and escaped via quoting when written back.
**Probe:** `source/github-helpers/search-query.test.ts` pins: tokenization w/ spaces (:15), parentheses (:20), all mutator verbs (:25–69), implicit defaults (:70), dedup (:80 'deduplicate is:pr/issue'), label-link parse (:93).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "SearchQuery deduplicateKeywords queryParts labelLinkRegex", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the part-array mutator + implicit-query table whenever editing a structured search DSL embedded in URLs. Adapt qualifier vocabulary. Keep the serializer quirks (trailing space, path rewrite) — they encode host behavior, not style. Direct tests present.
