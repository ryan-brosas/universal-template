<!-- capsule-v2 -->
# Entity-link resolution — normalize-once, batch-first, scope-sync

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you resolve free-text CSV values (emails, domains, names) to record IDs across columns, custom fields, and JSON arrays without scope leaks or N+1?

## EntityLinkResolver three-strategy dispatch
**Path/Symbol:** `packages/ImportWizard/src/Support/EntityLinkResolver.php` (whole, 352L): `batchResolve()` (:82-111), `resolveViaTeamMember()` (:156-166), `resolveViaCustomField()` (:172-201), `resolveViaJsonColumn()` (:239-305), `rejectInaccessibleEntities()` (:214-233).
**Signature:** `batchResolve(EntityLink $link, MatchableField $matcher, array $uniqueValues): array<string,int|string|null>`
**Data Shape:** Cache: `$cache[linkKey:field][normalizedValue] = id|null` (null cached too). Values normalized via `mb_strtolower(trim())`; blank ⇒ null BEFORE any query.

### Decisive source
```php
/**
 * Drop matches whose owning entity cannot be loaded for write (soft-deleted
 * or belonging to another team). The matcher reads custom_field_values
 * directly, bypassing model scopes; the executor loads records through the
 * default-scoped model query, so an unfiltered match becomes a silently
 * skipped row. Filtering here keeps the two in sync.
 */
$accessibleIds = $modelClass::query()
    ->where('team_id', $this->teamId)
    ->whereIn($keyName, array_values($valueToEntityId))
    ->pluck($keyName)->map(...)->flip();
return array_filter($valueToEntityId, fn ($id): bool => $accessibleIds->has((string) $id));
```
JSON-array matching is per-dialect SQL over exploded arrays — sqlite `json_each(CASE WHEN JSON_TYPE(...)='array' ... END)`, pgsql `CROSS JOIN LATERAL jsonb_array_elements_text(...)`, mysql `JSON_TABLE(IF(JSON_TYPE(...)='ARRAY',...))` — first-seen key wins, chunked at 5,000 values.

**Flow:** dispatch `match(true)`: User target → team-member OR team-owner pivot lookup; `custom_fields_*` field → definition lookup then scalar-column pluck or dialect-specific JSON explode; default → `pluck('id', $field)` on the target model. Results re-keyed through the SAME normalizer as inputs, so lookups are case/whitespace-insensitive by construction; every resolved value (misses included) lands in the cache.
**Invariant:** The raw CF-value table is read WITHOUT global scopes; therefore an explicit accessibility filter through the scoped model query is mandatory or matches point at soft-deleted/cross-team rows the executor cannot save.
**Probe:** `tests/Feature/ImportWizard/Support/EntityLinkResolverTest.php` (:17-73 team-member/owner/batch) + executor tests (:2460 soft-deleted domain not matched, :2483 re-import creates new company).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "EntityLinkResolver batchResolve rejectInaccessibleEntities resolveViaJsonColumn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt normalize-once-then-batch with cache-misses-including-nulls, the strategy dispatch (column / custom-field / user-pivot), and above all the accessibility-reconciliation step whenever one query bypasses scopes another enforces. Adapt the three SQL dialects to your engines. Omit CRM entity specifics. Direct tests pin both the happy paths and the soft-deleted trap.
