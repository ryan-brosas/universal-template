<!-- capsule-v2 -->
# Fan-out analysis — what are engines actually searching for?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How do you aggregate the sub-queries AI engines issue, measuring prompt-rewriting rather than echoes?

## Read-time exclusions + token-diff word changes
**Path/Symbol:** `apps/web/src/lib/fanout-analysis.ts:computeFanoutAnalysis` (L341–509), `promptKeywords` (L286–295), `tokenize` (L315–317), STOPWORDS rationale (L166–170).
**Signature:** `computeFanoutAnalysis(breakdown, modelTotals, promptValueMap, opts?): FanoutAnalysis`.
**Data Shape:** two read-time display rules applied in the reading SQL AND defensively here: (1) drop queries identical to the prompt — "a repeat says nothing about how the prompt was rewritten"; (2) drop the `unavailable` sentinel (aliased to the shared constant "so the two sides can't drift"). Word-change votes: each fanout query votes ONCE per distinct token (`Set` of query tokens vs prompt token set), weighted by row count.

### Decisive source
```ts
const promptTokens = promptTokensFor(row.prompt_id, promptValue);   // memoized per prompt
const queryTokens = new Set(tokenize(query));
for (const tok of queryTokens) if (!promptTokens.has(tok)) added.set(tok, (added.get(tok) ?? 0) + row.count);
for (const tok of promptTokens) {
	const target = queryTokens.has(tok) ? preserved : dropped;
	target.set(tok, (target.get(tok) ?? 0) + row.count);
}
```
Stopword list deliberately EXCLUDES "best", "top", "review(s)", "vs", "comparison", year numbers — "the modifiers that *are* the signal in fan-out research".

**Flow:** outputs cover totals/coverage-rate (brandMentionRate over fanout instances), top queries with drill-down refs (query→prompts and query→runs orderings), term cloud, added/dropped/preserved words, per-model and per-prompt breakdowns. Possessives contribute base form too ("Acme's" yields both tokens) because engines search the bare name.
**Probe:** covered by web test suite; pure module ("No DB or React imports… unit-tested in isolation").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "computeFanoutAnalysis promptKeywords UNAVAILABLE_SENTINEL wordChanges", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exclusion rules + one-vote-per-token diff; adapt caps (LIMITS) and stopword list to your domain — but keep commercial modifiers OUT of stopwords; omit breadth views if you have no cross-prompt page.
