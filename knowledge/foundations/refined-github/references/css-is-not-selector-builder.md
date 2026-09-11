<!-- capsule-v2 -->
# css-is-not-selector-builder — how do you compose `:is()`/`:not()` selector lists from arrays or variadics so features and the shared selector registry share one syntax?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** A 190-feature extension needs "match ANY of these host variants" and "exclude ANY of these" all the time, sometimes from inline literals, sometimes from precomputed arrays. How do you give every call site one tiny syntax that emits valid CSS?

## Dual-overload string builders
**Path/Symbol:** `source/helpers/css-selectors.ts` — `is` :1–6 (overloads :1–2, impl :3–6), `not` :8–13 (overloads :8–9, impl :10–13). Whole file 13 lines, zero imports.
**Signature:** `is(selectors: readonly string[]): string` | `is(firstSelector: string, ...otherSelectors: readonly string[]): string`; `not(…)` identical shape.
**Data Shape:** inputs are plain selector strings (array OR variadic); output is a single selector-list string `':is(a, b)'` / `':not(a, b)'`.

### Decisive source
```ts
export function is(firstSelector: readonly string[] | string, ...otherSelectors: readonly string[]): string {
	const selectors = Array.isArray(firstSelector) ? firstSelector : [firstSelector, ...otherSelectors];
	return `:is(${selectors.join(', ')})`;
}
// not(): identical body, `:not(` prefix
```

**Flow:** the implementation signature accepts BOTH shapes → `Array.isArray(firstSelector)` disambiguates (array form takes the array as-is; variadic form collects first + rest) → `join(', ')` emits a CSS selector list inside the pseudo-class.
**Invariant:** (1) the output is a PLAIN STRING by contract — callers concatenate it into larger expressions freely (`is(...) + ' ' + is(...) + not(...)`), so the builders must never return an object or add whitespace; (2) the dual overload exists precisely so precomputed arrays (`botAttributes = botNames.map(bot => `[href^="/${bot}"]`)` at selectors.ts:190, then `is(botAttributes)` at :196/:200/:220) and inline literals share one call site shape; (3) NO validation happens — a selector containing a comma would corrupt the list, so the contract is "pass simple selectors"; (4) order is preserved, no dedupe — `:is()`/`:not()` semantics (any-match OR / any-match exclude) come from CSS itself, not the builder.
**Probe:** no direct unit test upstream (pure function, untested — recorded honestly). Executed pins: `grep -n ":is(" source/helpers/css-selectors.ts` → line 5; `grep -n ":not(" source/helpers/css-selectors.ts` → line 12; `grep -c "Array.isArray" source/helpers/css-selectors.ts` → 2.

## Consumer evidence: three composition idioms across 17 import sites
**Path/Symbol:** `source/features/scrollable-areas.tsx` :10–24; `source/features/small-user-avatars.tsx` :58–67; `source/github-helpers/selectors.ts` :196, :248; `source/github-helpers/index.ts` :133–137.

### Decisive source
```ts
// scrollable-areas.tsx — multi-builder concatenation (comment: "must be kept in sync with the selectors in scrollable-areas.css")
const scrollableSelector = is('.comment-body', '[data-testid="markdown-body"]')
	+ ' '
	+ is('blockquote', 'pre') + not('.rgh-scrollable-expanded', 'blockquote *', 'pre *');
```
```ts
// small-user-avatars.tsx — static prefix + not() suffix
'.user-mention' + not('.opened-by > *', '.commit-author')
```
```ts
// selectors.ts — array form from a mapped constant, and is()+not() pair
'a[data-testid="avatar-icon-link"]' + is(botAttributes)
is(authorLinks) + not(authorLinksException)
```
```ts
// index.ts — transitional-selector idiom with a dated fallback
const navigationBarSelector = is('.GlobalNav',
	// Remove after June 2026
	'.js-repo-nav',
);
```

**Flow:** idiom 1 (concatenation): several builders joined with combinators (' ', ':not(…)' suffixes) build one complex expression — used where the same variant set must appear in JS observation AND the feature's CSS file (the sync comment makes the duplication explicit) → idiom 2 (prefix+suffix): a static anchor selector plus a `not()` exclusion tail → idiom 3 (registry sharing): the shared selector registry (selectors.ts) builds its constants with the SAME builders, so feature code and registry code cannot drift syntactically → idiom 4 (transitional): a dated comment inside the argument list marks a fallback selector for removal — the `:is()` list is the natural home for "old UI OR new UI" during a host redesign.
**Invariant:** the 17 import sites (grep count == graph `is` callers_total 17) span features AND github-helpers — the builders are the cross-layer selector vocabulary; a port that inlines `:is(…)` strings per feature loses the shared-syntax property that keeps the registry consistent.
**Probe:** executed pins above; consumer exemplars read directly this pass (scrollable-areas :10–24, small-user-avatars :58–67, selectors.ts :190–248, index.ts :133–137).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "css-selectors is not selector", mode: "ids" });
// top-2 line-exact: helpers.css-selectors.not 10-13 · helpers.css-selectors.is 3-6
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "is", direction: "inbound" });
// callers_total: 17 (matches whole-repo import-site grep count)
```
Executed 2026-08-28 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt verbatim — 13 lines, zero dependencies, zero host coupling; the dual-overload shape and the plain-string output contract are the entire design. Adapt nothing except your own selector lists. Omit nothing. If your port has a shared selector registry, route ALL `:is()`/`:not()` construction through these two functions so registry and feature code stay syntactically identical. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test (pure function left untested — recorded honestly); graph node present and line-exact. Cross-reference: selector-fixture-registry.md (the paired live-URL evidence registry this vocabulary feeds), observe-leaf-resolve-container.md (selector stability under CSS-module hash churn — why variant lists like navigationBarSelector exist).
