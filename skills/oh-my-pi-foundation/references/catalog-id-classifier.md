<!-- capsule-v2 -->
# Model-id classifier — how do you parse a model id into family/kind/version without classifying future releases as unknown?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How does a string like `claude-opus-4-8`, `gemini-3.5-flash-preview`, or a rolling alias become comparable structured metadata?

## Per-family parsers behind a null-memoizing wrapper, plus a precomputed SemVer table
**Path/Symbol:** `packages/catalog/src/identity/classify.ts:bareModelId` (:56), `parseKnownModel` (:65), `parser()` (:79), family parsers (:93/:108/:136/:160), `isAnthropicAdaptiveGenAtLeast` (:187), `precomputeTable` (:202), `parseSemVer` (:214), `compareSemVer` (:230).
**Signature:** `parseKnownModel(modelId): GeminiModel | AnthropicModel | OpenAIModel | UnknownModel`; `parser<T>(parse: (id) => T|null): (id) => T|null`; `parseSemVer(v: string): SemVer | null`; `semverGte(a, b)` accepts `SemVer | string`.
**Data Shape:** `SemVer {major,minor,patch}`; GLM adds `vision` (the `v` attached to the version: `glm-4.5v`) + suffix variant; unknown ids keep their bare form.

### Decisive source
```ts
// Caches the null result too, so repeated misses (the common case —
// other families' ids) stay O(1) and never re-run the regex work.
function parser<T>(parse: (modelId: string) => T | null): (modelId: string) => T | null {
  const cache = new Map<string, T | null>();
  return modelId => {
    const hit = cache.get(modelId);
    if (hit !== undefined || cache.has(modelId)) return hit ?? null;
    const result = parse(modelId);
    cache.set(modelId, result);
    return result;
  };
}

// Fast path for common 1–2 component versions; anything the table misses
// parses dynamically below so no FUTURE version ever classifies as unknown
// (the failure class #8256 fixed).
const SEMVER_PATTERN = /^(\d{1,2})(?:[.-](\d{1,2}))?(?:[.-](\d{1,2}))?$/;

// Rolling OpenAI aliases inherit wire capabilities from their current default
// snapshots — alias short-circuits the regex and pins the version directly.
const OPENAI_ALIAS_VERSIONS = { "daybreak-blue-latest": "5.6", /* … */ };
```

**Flow:** strip provider prefix (`lastIndexOf("/")`) → try gemini → anthropic → openai parsers in order → fall through to `{family:"unknown"}` → Anthropic tries kind-first THEN version-first (`claude-opus-4-8` vs `claude-4-8-opus`) → `-preview` suffix stripped before matching but NOT part of version.
**Invariant:** (1) memoize misses as well as hits — cross-family lookups dominate; (2) dynamic semver fallback under the precomputed table so an unseen future version still parses (never gate capability on "id not in table"); (3) rolling aliases map to concrete pinned versions because capability inheritance must be deterministic; (4) dotted AND dashed versions both parse (`4.7`, `4-7`) since Bedrock uses dashes while dates (`claude-opus-4-20250514` = 4.0) must not read as 20250514.
**Probe:** direct `packages/catalog/test/identity-family.test.ts:107` (`parseAnthropicModel` incl. dashed forms), `:138` (`supportsAdaptiveThinkingDisplay` excludes dated ids), `test/model-tokenizer.test.ts:21` (classifier consumers).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "parseKnownModel parseAnthropicModel parseSemVer classify", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the null-memoizing parser wrapper, dual-order anthropic parsing, and precompute-plus-dynamic-fallback SemVer; adapt family vocabularies to your supported vendors; omit the GLM/OpenAI variants if you don't serve them. Coverage caveat: none — direct unit tests pin every parser.
