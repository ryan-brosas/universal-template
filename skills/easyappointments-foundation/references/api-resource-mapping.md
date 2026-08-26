<!-- capsule-v2 -->
# api_resource field-mapping contract — how do you expose snake_case DB rows as camelCase API resources without injection holes?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How do models translate between wire resources and rows, and how are sort/field inputs neutralized?

## EA_Model kernel + per-model maps
**Path/Symbol:** `application/core/EA_Model.php:135` (`cast`), `:171` (`only`), `:188` (`optional`), `:210` (`db_field`), `:222` (`quote_order_by`, 222–259); example map `application/models/Webhooks_model.php:35-44`.
**Signature:** `db_field(string $api_field): ?string`; `quote_order_by(?string $order_by): ?string`
**Data Shape:** Each model declares `$casts = ['id'=>'integer', 'is_active'=>'boolean', …]` and `$api_resource = ['camelName' => 'snake_column', …]`.

### Decisive source
```php
// application/core/EA_Model.php:236-248 — strict column validation + backtick quoting before order_by
if (!preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$/', $column)) {
    continue; // Skip invalid column names — no SQL injection through the column name
}
if (strpos($column, '.') !== false) {
    $column_parts = explode('.', $column);
    $column = '`' . $column_parts[0] . '`.`' . $column_parts[1] . '`';
} else {
    $column = '`' . $column . '`';
}
```

**Flow:** controllers accept camelCase JSON → `api_decode(&$resource, ?array $base)` copies ONLY mapped keys (keyExists-guarded; `$base` seeds updates so partial PATCHes don't null fields) → model save validates+casts → responses go through `api_encode` (explicit projection, id cast to int) → optional `only()`/`fields=` narrowing → `load()` attaches relations. Sorting: `Api::request_order_by` (`application/libraries/Api.php:200-235`) maps each `-/+camel` token via `db_field`, silently SKIPPING unmapped fields, then the surviving string is regex-gated and backtick-quoted by `quote_order_by`.
**Invariant:** TWO independent injection gates — the api_resource whitelist (unknown sort fields dropped at :225-227) AND the regex+backtick sanitizer (defense in depth if a caller bypasses db_field). Casting is explicit per-model (MySQL drivers return strings; `'is_active' => 'boolean'` prevents `false == '0'` traps). Porters who keep only one gate or trust client column names reopen ORDER BY injection.
**Probe:** `grep -cF '[a-zA-Z_][a-zA-Z0-9_]' application/core/EA_Model.php` (= 1: the column-validation regex at :238).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "quote_order_by db_field", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-gate sort sanitization + keyExists-guarded decode with base-seeding + explicit encode projections; adapt naming to your conventions but keep BOTH gates; omit the deprecated `get_value/get_row/get_batch/add` shims on EA_Model (:69-125). Direct tests: `tests/Unit/Helper/ArrayHelperTest.php` + `ValidationHelperTest.php` cover adjacent helpers only — this capsule is source-pinned.
