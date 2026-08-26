<!-- capsule-v2 -->
# Header auto-mapping — normalized header grammar over keys, labels, and guesses

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you auto-map arbitrary CSV headers to fields and relations without exact-name brittleness?

## EntityLink::matchesHeader + guess ladders
**Path/Symbol:** `packages/ImportWizard/src/Data/EntityLink.php`: `matchesHeader()` (:248-255), `normalizeHeader()` (:257-260), `fromCustomField()` guesses (:125-130); twin logic on ImportField (`buildCustomFieldGuesses` in BaseImporter :218-233 adds singular forms).
**Signature:** `matchesHeader(string $header): bool`; `normalizeHeader(string $value): string // lower -> [-_]→space -> squish`
**Data Shape:** Candidate set per link: `[key, label, ...guesses]`; CF links generate `{code, name, lowercase name, underscored name}`; entity presets add domain synonyms (`company, company_name, organization, account, employer`).

### Decisive source
```php
private function normalizeHeader(string $value): string
{
    return str($value)->lower()->replace(['-', '_'], ' ')->squish()->toString();
}
public function matchesHeader(string $header): bool
{
    $normalized = $this->normalizeHeader($header);
    $candidates = array_merge([$this->key, $this->label], $this->guesses);
    return array_any($candidates, fn (string $candidate): bool => $this->normalizeHeader($candidate) === $normalized);
}
```

**Flow:** upload step reads headers → each unmapped header tested against every field/link candidate through ONE normalizer (both sides normalized — no per-candidate rules) → first match wins; unmatched columns stay user-mappable → singular/plural variants pre-generated for codes and names.
**Invariant:** Normalization must be applied to BOTH sides with the SAME function (asymmetric normalization = the classic "Company ID" never matches `company_id` bug); matching is exact-after-normalize, NOT fuzzy substring.
**Probe:** exercised via MappingStepTest / PreviewStepTest suites; no isolated matcher unit file at this pin (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "EntityLink matchesHeader normalizeHeader guesses ImportField", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt symmetric normalize-then-compare with generated synonym/singular candidates. Extend the normalizer cautiously (case-fold + separator squash is the portable core). Omit the CRM synonym lists. Caveat: indirect test coverage via step suites.
