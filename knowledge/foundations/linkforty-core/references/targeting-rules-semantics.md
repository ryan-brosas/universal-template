<!-- capsule-v2 -->
# Targeting rules AND-semantics — countries ∧ devices ∧ languages, primary-language extraction, 404-on-miss

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do per-link audience rules combine, and what happens to a visitor matching none?

## targeting_rules evaluation in handleRedirect
**Path/Symbol:** `src/routes/redirect.ts:294-337`; debug mirror at `src/routes/debug.ts:66-106` (per-dimension detail incl. prefix-match variant); schema in `src/routes/links.ts:43-47`.
**Signature:** `rules?: { countries?: string[]; devices?: ('ios'|'android'|'web')[]; languages?: string[] }` — stored JSONB, default `{}`.
**Data Shape:** Empty/absent rule arrays are ignored (no constraint); a visitor failing ANY present dimension gets 404 `Link not found` — identical to unknown-code response, so targeting misses leak nothing.

### Decisive source
```ts
// redirect.ts:311-331 (one dimension shown; all three follow the same shape)
if (rules.countries && rules.countries.length > 0) {
  const targetCountries = rules.countries.map((c) => c.toUpperCase());
  if (!countryCode || !targetCountries.includes(countryCode.toUpperCase())) {
    isTargeted = false;
  }
}
// :333-336
if (!isTargeted) {
  return reply.status(404).send({ error: 'Link not found' });
}
```

**Flow:** evaluated BEFORE redirect decision and before click tracking → country compares uppercased ISO codes against geoip lookup (missing geo ⇒ fail) → device compares detectDevice output → language takes `accept-language.split(',')[0].split('-')[0].toLowerCase()` (primary subtag only: `en-US,en;q=0.9` → `en`) and fails when absent. The debug simulate endpoint mirrors the same semantics but matches languages by PREFIX (`lang.startsWith(primaryLang)`), a deliberate looser twin for diagnostics.
**Invariant:** Dimensions AND together; within a dimension any-listed-value passes; absent visitor data (no geo, no language header) FAILS a present constraint rather than passing; miss returns the unknown-code body.
**Probe:** `bash -c "grep -cF 'isTargeted = false' src/routes/redirect.ts"` → 3 (:314 country + :321 device + :329 language arms — the `let isTargeted = true` initializer is NOT a match); direct tests: no dedicated route test file pins redirect targeting (debug.ts simulation covers intent); recorded as honest caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "targeting_rules countries devices languages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt AND-of-dimensions with any-of-values inside each and data-absent-fails semantics; adapt dimensions (add OS/version etc.); omit the 404-camouflage only if your product wants soft fallbacks to original_url instead.
