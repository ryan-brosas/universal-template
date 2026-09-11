<!-- capsule-v2 -->
# Generated-source skip — how do you keep minified bundles from DoSing the extractor?

**Source:** pi-fovea MIT `main@5bd4e6f`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** A single 800 KB one-line bundle can make pattern matching emit gigabytes and hang for a minute per invocation — where is the content-based tripwire, and why do skipped files still get fact entries?

## Name convention + huge-line tripwire, fact-free but cached
**Path/Symbol:** `src/core/build.ts:isGeneratedSource` (:116-131, `MINIFIED_LINE_CHARS=4_000`, `GENERATED_NAME_RE`), consumed in loadFacts/refreshFacts; report bucket `ExtractionReport.generated` (:59-66); `CACHE_VERSION = 11` (:68) bumped for exactly this semantic.
**Signature:** `isGeneratedSource(rel: string, text: string): boolean`.
**Data Shape:** generated files get REAL fact records (empty symbols/imports/calls/literals) that ARE persisted — they land in `store.generated`, deliberately NOT in `store.tainted`; the report lists them under `generated[]`.

### Decisive source
```ts
// Minified/generated bundles parse fine but blow up ast-grep pattern matching:
// `$F($$$A)` over duckdb's 800 KB single-line worker emitted 7.5 GB of match
// JSON and took ~46 s per invocation. Real source lines never run thousands
// of chars, so a huge line (or a conventional generated name) marks the file
// for fact-free skipping — same treatment as oversized, no extraction at all.
const MINIFIED_LINE_CHARS = 4_000;
const GENERATED_NAME_RE = /\.(?:min|bundle)\.(?:[cm]?js|[cm]?ts|jsx|tsx|mjs|cjs)$/i;
export const isGeneratedSource = (rel: string, text: string): boolean => {
  if (GENERATED_NAME_RE.test(rel)) return true;
  if (text.length < MINIFIED_LINE_CHARS) return false;
  ... // any line ≥ 4000 chars ⇒ true
};
```

**Flow:** name matches `.min./.bundle.` convention OR any single line ≥4k chars (checked without building substrings) → skip extraction entirely → record empty facts + `store.generated` marker so the cache stays consistent → if the file later becomes real source, its sha changes and normal re-extraction resumes automatically (content-addressed cache does the unpick).
**Invariant:** skipping is an HONESTY category, not a failure: reported in every status render, never silently thinning the graph; generated ≠ tainted — nothing failed, so warm starts keep the decision; a false positive self-heals on next content change because the tripwire re-evaluates only on re-read.
**Probe:** `tests/generated.test.ts` — "flags single-line minified bundles by content" (:26-29, incl. long-single-token no-newline case); "flags conventional generated names" (:31-34, tiny file with .min.js name IS generated); "records fact-free entries for minified files without extraction" (:44-57, asserts `tainted` stays false); "re-extracts when a generated file turns into real source" (:59-69).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "isGeneratedSource MINIFIED_LINE_CHARS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-signal tripwire + honest reporting before feeding untrusted-repo sources to any pattern matcher. Adapt the 4k threshold/name regex to your ecosystem. Omit the cache-version coupling detail.
