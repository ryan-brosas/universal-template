<!-- capsule-v2 -->
# Bounded RFC 6570 URI templates — which limits keep template expansion and matching off the ReDoS/OOM list, and what do `?`-to-`&` continuation and exploded matching require?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When porting resource URI templates, which grammar subset and guards prevent hostile templates/URIs from hanging the server?

## Template engine
**Path/Symbol:** `packages/core-internal/src/shared/uriTemplate.ts`: limits (:5-8), `isTemplate` (:16-20), parse loop (:44-88), `expandPart` (:112-170), `expand` (:172-194), `partToRegExp` (:200-253), `match()` (:255-289).
**Signature:** `new UriTemplate(template: string)`; `.expand(variables): string`; `.match(uri): Variables | null`; static `UriTemplate.isTemplate(str)`.
**Data Shape:** limits — template 1MB, variable name/value 1MB, ≤10,000 expressions, generated regex 1MB; operators `{+ # . / ? &}` + plain/exploded (`*`); values `string | string[]`.

### Decisive source
```ts
// :5-8 the four bounds (every entry point validates BEFORE work)
const MAX_TEMPLATE_LENGTH = 1_000_000;
const MAX_VARIABLE_LENGTH = 1_000_000;
const MAX_TEMPLATE_EXPRESSIONS = 10_000;
const MAX_REGEX_LENGTH = 1_000_000;
```
```ts
// :186-190 ? degrades to & after the first query parameter
result += (part.operator === '?' || part.operator === '&') && hasQueryParam ? expanded.replace('?', '&') : expanded;
if (part.operator === '?' || part.operator === '&') { hasQueryParam = true; }
```

**Flow:** constructor parses once (unclosed `{` throws; expression counter caps runaway nesting); expand: `?`/`&` render only DEFINED vars as `name=value` pairs joined by the right separator; multi-name composites comma-join defined values; operators prefix (`#`, `.`, `/`) or pass reserved chars through (`+`, `#` use `encodeURI`, others `encodeURIComponent`). match: parts compile to anchored regex fragments (`([^/,]+)` plain, exploded `(…(?:,…)*)`, query params `name=([^&]+)` with `&` between), then captured groups split on commas when exploded. `match` re-validates URI + generated-pattern length so a pathological input dies as a thrown Error, not a hang.

**Invariant:** the regex is built from ESCAPED literal text plus bounded character classes — never from user data interpolated raw; every length check fires BEFORE regex construction, so the "generated pattern" blowup class is structurally unreachable. Exploded matching splits on the FIRST-level comma only; porters who unconditionally split non-exploded captures corrupt values containing commas.

**Probe (direct tests):** `packages/core-internal/test/shared/uriTemplate.test.ts` 'security and edge cases' :201-249 — 'should handle extremely long input strings' :202 (100k-char round-trip), 'deeply nested template expressions' :209, 'malformed template expressions' :227 (`{unclosed` throws, `{}`/`{,}` legal), 'pathological regex patterns' :234 (must not throw/hang), 'invalid UTF-8 sequences' :241.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "UriTemplate match expand expression limit", limit: 2 });
// → UriTemplate.match Method 255-289 rank #1
```

## Verdict
Adopt the bounded parser/compiler pair verbatim for any resource-template matcher; adapt operator coverage to the RFC subset you need; omit label/reserved operators if your URIs are path+query only.
