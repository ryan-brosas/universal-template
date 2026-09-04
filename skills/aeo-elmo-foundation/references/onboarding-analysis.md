<!-- capsule-v2 -->
# Onboarding brand analysis — how do you turn a URL into a trackable identity?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How is one structured LLM call converted into canonical brand name, domains, aliases, competitors, and prompt set?

## Schema-is-contract + paranoid normalization
**Path/Symbol:** `packages/lib/src/onboarding/analyze.ts:buildSchema` (L57–85), `buildAnalysisContext` (L147–180), `normalize` (L284–365), `filterRedundantAliases` (L222–226); provider selection `onboarding/llm.ts:resolveResearchProvider` (L55–82); domain hygiene `onboarding/utils.ts` (whole).
**Signature:** `analyzeBrand(options): Promise<OnboardingSuggestion>`; `runStructuredResearchPrompt(prompt, schema): Promise<T>`.
**Data Shape:** Zod schema with `.describe()` carrying the quality bar (brandName "must be searchable, because mention-detection matches it as a substring"; prompts lowercase <12 words, MAJORITY unbranded; ≤3 tags from a ≤5-value shared vocabulary). `generateObject` derives the JSON schema, so field shapes live in exactly one place.

### Decisive source
```ts
// A caller-supplied name wins: it's what the user asked to track, and for a
// sub-brand the model tends to answer with the parent it recognises
// ("Nike Golf" → "Nike"), which would silently widen every match.
const brandName = providedBrandName ?? ((raw.brandName || brandNameHint).trim() || brandNameHint);
…
return aliases.filter((a) => !a.toLowerCase().includes(canonical));
// dedupe at competitor level: any shared domain skips the whole entry
if (cleaned.some((d) => seenCompetitorDomains.has(d))) continue;
```

**Flow:** cleanUrl/cleanDomain (strip credentials — value goes to external services; keep path for sub-brand scope note) → optional Jina-then-Readability website excerpt (fail-open to "") → one web-search-enabled structured call → normalize: kebab-case tags (≤3), lowercase+dedupe prompts (≤max), validate competitor domains against DOMAIN_REGEX, exclude brand-owned domains from competitors. The refusal-proofing instruction ("Refusing to produce JSON… is a failure mode") is IN THE PROMPT because empty-object beats no-object downstream.
**Invariant:** tracked identity = hostname ONLY (`website: normalizedWebsite`) while analysis may use the full sub-page URL; provided names outrank model guesses; alias list must be substring-minimal or mention detection double-counts.
**Probe:** `packages/lib/src/onboarding/analyze.test.ts` + `llm.test.ts` + `utils.test.ts` (42 GREEN here incl. provider preference ladder and env override).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "analyzeBrand buildAnalysisContext normalize filterRedundantAliases resolveResearchProvider", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt schema-as-source-of-truth + normalize-after-generate + hostname-vs-analysis-URL split; adapt the excerpt fetcher; omit the whitelabel report reuse only if you have no batch flow.
