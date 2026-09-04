<!-- capsule-v2 -->
# Session-data flattening & typed storage — how do arbitrary identify() JSON payloads become queryable typed key-value rows?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How is nested JSON flattened, type-tagged, truncated, and upserted per (session, key)?

## session-data-flattening
**Path/Symbol:** `src/lib/data.ts:flattenJSON :11-25, createKeyValue :63-92, getStoredStringValue :46-55`; writer `src/queries/sql/sessions/saveSessionData.ts:26-118`; tests `src/queries/sql/sessions/saveSessionData.test.ts`.
**Signature:** flatten → `{key: 'a.b.c', value, dataType}` rows; dataType ∈ string|number|boolean|date|array (objects→array=JSON.stringify; ISO-strings detected as date by DATETIME_REGEX).
**Data Shape:** CH row `{data_key, data_type, string_value, number_value, date_value, distinct_id}`; Postgres upserts ON CONFLICT `(session_id, data_key)`.

### Decisive source
```ts
// data.ts — the typing rules:
case 'boolean': dataType = DATA_TYPE.boolean; processedValue = value ? 'true' : 'false'; break;
...
case 'object': dataType = DATA_TYPE.array; processedValue = JSON.stringify(value); break;
// oversize arrays are DROPPED to null rather than truncated garbage:
if (dataType === DATA_TYPE.array && stringValue.length > FIELD_LENGTH.stringValue) return null;
```
```ts
// saveSessionData.ts relational side — idempotent identity writes:
on conflict (session_id, data_key)
do update set string_value = excluded.string_value, ..., created_at = coalesce({{createdAt}}, session_data.created_at)
```

**Flow:** identify payload → recursive flatten (dot-joined keys; arrays and dates are LEAVES) → typed columns with truncation via truncateString + FIELD_LENGTH table → CH: kafka-or-direct insert of one message per leaf; PG: sequential upsert preserving first-seen created_at.
**Invariant:** booleans are stored as the STRINGS 'true'/'false' (CH has no bool column in this schema) — filtering code must compare against strings. The conflict clause makes repeated identifies IDEMPOTENT per key (last write wins) without duplicating rows.
**Probe:** `grep -c "describe(" src/queries/sql/sessions/saveSessionData.test.ts` → 2 (runQuery mocked); structural pins: `grep -n "on conflict (session_id, data_key)" src/queries/sql/sessions/saveSessionData.ts` → :85.
**Probe:** `grep -c "JSON.stringify(value)" src/lib/data.ts` → 1.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "flattenJSON createKeyValue saveSessionData upsert", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt dot-key flattening into typed KV rows for user-supplied properties; adapt FIELD_LENGTH limits; keep drop-not-truncate for oversized arrays if you query them as JSON lists.
