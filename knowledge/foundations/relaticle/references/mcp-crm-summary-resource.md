<!-- capsule-v2 -->
# CRM summary resource — raw SQL over the EAV table with graceful field absence

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you aggregate pipeline-by-stage and overdue-task metrics when stages/amounts live in user-defined EAV rows?

## CrmSummaryResource handle()
**Path/Symbol:** `app/Mcp/Resources/CrmSummaryResource.php` (whole, 163L): `handle()` (:44-61), `opportunitySummary()` (:66-121), `taskSummary()` (:126-151), `resolveFieldId()` (:153-162).
**Signature:** `#[Uri('relaticle://summary/crm')] #[MimeType('application/json')] Resource::handle(Request): Response`
**Data Shape:** `{companies:{total}, people:{total}, opportunities:{total, by_stage{label:{count,total_amount}}, total_pipeline_value, total_won_value}, tasks:{total, overdue, due_this_week}, notes:{total}}` — 60s cache per team.

### Decisive source
```php
$stageFieldId = $this->resolveFieldId($teamId, 'opportunity', OpportunityField::STAGE->value);
$amountFieldId = $this->resolveFieldId(...);
if ($stageFieldId === null) { return ['total' => $total]; }   // degrade, never throw

$amountJoin = $amountFieldId !== null ? "LEFT JOIN custom_field_values amount_cfv
    ON amount_cfv.entity_id = o.id AND amount_cfv.entity_type = 'opportunity'
    AND amount_cfv.custom_field_id = ?" : '';
...
GROUP BY stage_cfv.string_value
```
Stage labels resolved back through `custom_field_options` (`$stageOptions[$stageId] ?? $stageId`); "won" detection is label-substring `str_contains(strtolower($stageLabel),'won')`. Task plane uses Postgres FILTER aggregates: `COUNT(*) FILTER (WHERE due_cfv.datetime_value::date < CURRENT_DATE)`.

**Flow:** read-ability gated via `shouldRegister()` (same token rule as prompts) → counts per entity scoped by team_id + soft-delete guard in raw SQL → stage field missing ⇒ totals-only degradation; AMOUNT field missing ⇒ zero-dollar join omitted entirely → option IDs translated to human labels before returning JSON.
**Invariant:** Every custom-field join must carry entity_type AND custom_field_id AND the outer soft-delete predicate; a missing definition degrades the metric shape rather than erroring — assistants handle absent keys better than failed resources.
**Probe:** `tests/Feature/Mcp/CrmSummaryResourceTest.php` (dedicated suite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CrmSummaryResource opportunitySummary taskSummary resolveFieldId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt EAV-side raw SQL with per-field existence degradation for analytics over user-defined schemas. Adapt FILTER syntax to your dialect. Omit Postgres-specific casts if portable SQL is required. Dedicated direct test suite.
