<!-- capsule-v2 -->
# Search config overlay — how do you default network-request knobs from user config so the provider can never see an under-specified option set?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** How do you default network-request knobs from user config so the provider can never see an under-specified option set?

## Two-layer defaulting: z-schema parse defaults + apply()-time ??-ladder over the SAME constants
**Path/Symbol:** `src/search.ts` `DEFAULT_OPENAI_CODEX_SEARCH_{MODEL,MODE,CONTEXT_SIZE,MAX_OUTPUT_TOKENS}` (`:29/:32/:35/:38`) + vocabularies `OpenAICodexSearchMode`/`'cached'|'indexed'|'live'` and `OpenAICodexSearchContextSize`/`'low'|'medium'|'high'` (`:41-44`); binding at `src/index.ts` Config schema (`:148-151`) and `apply()` (`:192-195`).
**Signature:** Constants `'gpt-5.6-sol' | 'cached' | 'medium' | 10_000`; `searchMaxOutputTokens` bound by `z.number().step(1).min(1)`.
**Data Shape:** Four scalar defaults plus two closed string-literal unions; both binding layers import the SAME module-level constants — there is no second source of default values.

### Decisive source
```ts
// src/index.ts :148-151 — layer 1: parse-time schema defaults
searchModel: z.string().default(DEFAULT_OPENAI_CODEX_SEARCH_MODEL),
searchMode: z.union(['cached', 'indexed', 'live'] as const).default(DEFAULT_OPENAI_CODEX_SEARCH_MODE),
searchContextSize: z.union(['low', 'medium', 'high'] as const).default(DEFAULT_OPENAI_CODEX_SEARCH_CONTEXT_SIZE),
searchMaxOutputTokens: z.number().step(1).min(1).default(DEFAULT_OPENAI_CODEX_SEARCH_MAX_OUTPUT_TOKENS),

// src/index.ts :192-195 — layer 2: apply() ??-ladder over the SAME imports
model: config.searchModel ?? DEFAULT_OPENAI_CODEX_SEARCH_MODEL,
mode: config.searchMode ?? DEFAULT_OPENAI_CODEX_SEARCH_MODE,
contextSize: config.searchContextSize ?? DEFAULT_OPENAI_CODEX_SEARCH_CONTEXT_SIZE,
maxOutputTokens: config.searchMaxOutputTokens ?? DEFAULT_OPENAI_CODEX_SEARCH_MAX_OUTPUT_TOKENS,
```

**Flow:** host parses plugin config (schema applies `.default(DEFAULT_*)`, vocabulary unions + integer≥1 budget bound enforced at parse time) → `apply()` re-applies the `??`-ladder over the same imported constants so even a hand-built options object cannot be under-specified → fully-resolved options reach `OpenAICodexSearchProvider` → wire body carries `settings.search_context_size`, mode-mapped `external_web_access` (false/'indexed'/true), and `max_output_tokens`.
**Invariant:** The provider must never observe an undefined search knob; defaulting exists in BOTH layers and both layers reference one constant source, so changing a default cannot desynchronize schema validation from runtime construction.
**Probe:** `tests/search.spec.ts :204-266` — the composite-plugin case drives the REAL apply() with explicit `{searchMode:'live', searchContextSize:'high', searchMaxOutputTokens:321}` and pins the recorded session-event wire body field-for-field including `external_web_access: true`. Honest caveat: the unit fixture (`:54-66`) always passes EXPLICIT options ('gpt-search-test'/1234), so default VALUES are unexercised by any spec — evidence is type-checking plus the real-apply registration path.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", qn_pattern: "^dsh-codex\\.src\\.search\\.DEFAULT_OPENAI_CODEX_SEARCH_.+$", limit: 10 });
// observed live: total 4, has_more=false — the four constants at :29/:32/:35/:38
await mcp.codebase_memory.query_graph({ project: "dsh-codex", query: "MATCH (a)-[u:USAGE]->(v:Variable) WHERE v.name STARTS WITH 'DEFAULT_OPENAI_CODEX_SEARCH_' RETURN v.name AS constant, a.qualified_name AS consumer" });
// observed live: total 8 rows = exactly TWO consumers per constant (dsh-codex.src.apply + dsh-codex.src.index)
```

## Verdict
Adopt dual-layer defaulting from one constant source with closed vocabularies validated at parse time. Adapt config key names and bounds to the host's settings grammar. Omit the Codex endpoint/body specifics (owned by search-provider). Coverage caveat: check_index_coverage clean for src/search.ts, src/index.ts, tests/search.spec.ts.
