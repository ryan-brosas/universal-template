<!-- capsule-v2 -->
# Model display-name cleaning — which name decorations are noise and which are identity?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you normalize aggregator model names ("OpenRouter: Claude … (latest) ($$$$)") without erasing meaningful variant tags?

## Author-prefix strip + extrinsic-tag regex with empty-guard
**Path/Symbol:** `packages/catalog/src/utils.ts:AUTHOR_PREFIX` (:56), `NOISE_TAGS` (:61), `cleanModelName` (:66); applied in `build.ts:buildModel` (:87).
**Signature:** `cleanModelName(name: string): string` — returns input verbatim when stripping would leave nothing.
**Data Shape:** `AUTHOR_PREFIX = /^[A-Za-z][A-Za-z0-9 .+&'-]{0,23}: /`; `NOISE_TAGS = /\s*\((?:latest|Antigravity|\$+|>?\d+% off|retires [^)]*)\)/g` (global).

### Decisive source
```ts
// Model-extrinsic decorations removed; VARIANT tags that map to distinct
// wire ids — "(Thinking)", "(free)", "(Fast)", dates, regions, sizes — STAY.
// Stripping order matters: author prefix, then tags, then space collapse.
const cleaned = name.replace(AUTHOR_PREFIX, "").replace(NOISE_TAGS, "").replace(/ {2,}/g, " ").trim();
return cleaned.length > 0 ? cleaned : name;
```

**Flow:** discovery hands a raw gateway name to `buildModel` → prefix (≤24 chars before `": "`) dropped → promo/lifecycle/price-tier tags dropped → whitespace collapsed → empty result guards back to the original.
**Invariant:** (1) never strip a tag that distinguishes a wire id — thinking/free/fast survive by design; (2) the function is total: worst case is the input unchanged.
**Probe:** direct `packages/catalog/test/build.test.ts:165` ("strips gateway author prefixes and extrinsic tags from display names"), `:179` ("keeps variant tags that map to distinct wire ids").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "cleanModelName NOISE_TAGS AUTHOR_PREFIX", limit: 5, fields: ["signature", "file"] });
```

## Verdict
Adopt the extrinsic-vs-variant distinction and empty-guard; adapt the vocabularies to your aggregators' fashions; omit if names arrive clean. Coverage caveat: none.
