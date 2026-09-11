<!-- capsule-v2 -->
# Website excerpt ladder — how do you get readable text from an arbitrary site?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** What fetch strategy survives bot blocks and JS-only sites while staying dependency-light?

## Jina reader, then self-hosted Readability
**Path/Symbol:** `packages/lib/src/website-excerpt.ts:getWebsiteExcerpt` (L33–61), `fromJina` (L68–83), `fromReadability` (L91–117), `toExcerpt` (L120–122).
**Signature:** `getWebsiteExcerpt(url: string): Promise<string>` — returns `""` when every source fails (best-effort miss, never throws).
**Data Shape:** excerpt bounded to 200 LINES (`split("\n").slice(0,200)`) — line-count bound without reflowing extracted text. Browser UA string on both paths ("less likely to be treated as bot traffic than a custom UA").

### Decisive source
```ts
const sources = [
	{ name: "jina", fetch: () => fromJina(cleanUrl) },          // r.jina.ai — renders JS, anonymous OK
	{ name: "readability", fetch: () => fromReadability(cleanUrl) }, // own fetch + @mozilla/readability + linkedom
];
for (const source of sources) {
	try { const content = await source.fetch(); if (content) return toExcerpt(content); … }
	catch … // fall through
}
```
Jina note in-source: anonymous requests from some IP ranges get 401 "bad network reputation"; setting optional `JINA_API_KEY` switches rate-limiting to per-key and sidesteps the block. Readability path requires content-type html; falls back to whole-body text when no article isolates.

**Flow:** scheme-normalize (`https://` prefix when missing) → try sources in order → first non-empty wins → 200-line cap. Callers treat "" as acceptable context loss (onboarding proceeds with just the domain).
**Invariant:** fail-open with diagnostics at every rung; a blocked/rate-limited source must degrade, not abort brand analysis.
**Probe:** `packages/lib/src/website-excerpt.test.ts` (10 GREEN here: source ordering, empty-vs-failure, cap behavior).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "getWebsiteExcerpt fromJina fromReadability toExcerpt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-rung fail-open ladder and line-based cap; adapt source list to your environment (drop Jina if outbound SaaS is unacceptable); omit nothing else.
