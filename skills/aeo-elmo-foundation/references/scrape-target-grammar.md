<!-- capsule-v2 -->
# Scrape-target grammar — how is a tracking target configured without a config file?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How can one env var express every model/provider/version/web-search combination an operator tracks, and what does each colon segment mean?

## model:provider[:version][:online]
**Path/Symbol:** `packages/config/src/scrape-targets.ts:parseScrapeTargets` (L27–47), `formatScrapeTarget` (L54–62), `STATUS_TARGETS` (L69–118).
**Signature:** `parseScrapeTargets(envValue?: string): ModelConfig[]`; `formatScrapeTarget(config: ModelConfig): string`.
**Data Shape:** `ModelConfig = { model, provider, version?, webSearch }`. Comma splits entries; within an entry, split on `":"` — first segment = model, second = provider; if the LAST segment is literally `"online"` it pops as the web-search flag; all remaining middle segments rejoin with `":"` as the version slug. That rejoin is what lets OpenRouter variant slugs like `anthropic/claude-sonnet-5:free` survive.

### Decisive source
```ts
const parts = trimmed.split(":");
if (parts.length < 2) throw new Error(`Invalid SCRAPE_TARGETS entry: "${trimmed}" (need at least model:provider)`);
const webSearch = parts[parts.length - 1] === "online";
const versionParts = parts.slice(2, webSearch ? -1 : undefined);
const version = versionParts.length > 0 ? versionParts.join(":") : undefined;
```

**Flow:** worker/CLI parse `SCRAPE_TARGETS` once per firing (`parseScrapeTargets(process.env.SCRAPE_TARGETS)`); empty/unset throws with a worked example in the message; `validateScrapeTargets` (providers/config.ts) then checks each target against its provider's `isConfigured()` + `validateTarget`, and demands a version slug for every direct-API provider.
**Invariant:** the parse must be invertible — `format(parse(x)) === x` and `parse(format(c))` deep-equals `c` are both test-pinned, so the same grammar is safely reused for the `ONBOARDING_LLM_TARGET` override and for status-page display.
**Probe:** `packages/config/src/scrape-targets.test.ts` (round-trip both directions; `providersByModel` derived from STATUS_TARGETS covers every model it names).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "parseScrapeTargets formatScrapeTarget ModelConfig providersByModel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-segment grammar and last-segment-online rule verbatim — it is the whole configuration surface; adapt the direct-API-requires-version rule to your provider set; omit STATUS_TARGETS (it exists so the public status page and the CI provider test read one list and cannot drift).
