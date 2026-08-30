<!-- capsule-v2 -->
# Geo string classifier — how do I split "Amsterdam Oud-West, North Holland Province, Netherlands" into city/province/country without an API?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** How do I resolve the ambiguity of a comma-split location when part-count doesn't pin the roles?

## Part-count ladder + membership checks
**Path/Symbol:** `src/utils/index.ts:getLocationFromText` (:44–127); predicates `getIsCountry` (:7–18), `getIsCity` (:20–28).
**Signature:** `getLocationFromText(text): Location | null`; `Location = { city: string|null, province: string|null, country: string|null }`.
**Data Shape:** input like `"Sacramento, California Area"`; helpers backed by `i18n-iso-countries` name table + `all-the-cities` dataset, each with hand-added overrides (`'united states'`, `'the netherlands'`, `'new york'`) for names the datasets miss.

### Decisive source
```ts
if (parts.length === 3) { /* city, province, country — order trusted */ }
if (parts.length === 2) {
  if (getIsCity(parts[0]) && getIsCountry(parts[1]))
    return { city: parts[0], province, country: parts[1] }
  if (getIsCity(parts[0]) && !getIsCountry(parts[1]))
    return { city: parts[0], province: parts[1], country }
  return { city, province: parts[0], country: parts[1] } // fallback: province, country
}
// 1 part: country? → city? → else assume province
return { city, province: parts[0], country }
```

**Flow:** strip `' Area'` suffix → split on `', '` → three parts = positional certainty; two parts = the ambiguous case, resolved by membership testing BOTH fragments against reference datasets; one part = classify by predicate priority (country → city → default-province). Every branch returns the FULL three-field shape with `null` placeholders — never a partial object.
**Invariant:** ambiguity is resolved by DATA MEMBERSHIP (is this fragment a known city/country?), not by position guessing; unknown text degrades to the most-plausible role (province) instead of failing. Null-preserving throughout — mirrors the raw→clean parse contract. The override lists are load-bearing: real profiles say "United States" and "The Netherlands" in forms ISO tables miss.
**Probe:** `src/utils/index.test.ts::describe('getLocationFromText')` — pins `'Sacramento, California Area'` → `{city:'Sacramento', province:'California Area', country:null}` and friends WITHOUT any network or browser.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "getLocationFromText getIsCity getIsCountry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the part-count ladder + membership predicates + full-shape-null-placeholder returns for any free-text geo normalization (profiles, job postings, company HQs). Adapt the backing datasets and override lists per locale. Omit the specific npm deps if you have equivalent data. This fills a gap in the suite's `profile-schema.md`, which canonicalizes URLs but not location strings.
