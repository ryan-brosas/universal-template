<!-- capsule-v2 -->
# Property-filter subquery trio — how do you filter events by their dynamic event_data / session_data key-value rows?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How do per-row property filters, multi-property AND groups, and session-scoped variants compile in each backend?

## property-filter-trio
**Path/Symbol:** `src/lib/clickhouse.ts:getPropertyFilterQuery :268-462, getEventPropertyFilterQuery :464-561, getSessionPropertyFilterQuery :565-634`; prisma twins `src/lib/prisma.ts:338-716`.
**Signature:** `(filters: PropertyFilter[{propertyName,dataType,operator,value}], timezone?) -> { sql, params }` with indexed params `epf_key_N`/`epf_val_N`.
**Data Shape:** dataType enum (string/number/date/array/boolean) selects the `*_value` column and coercion; array values JSON-extracted.

### Decisive source
```ts
// Event properties: one row can't satisfy two conditions ⇒ GROUP BY + HAVING max(if(...))=1
clauses.push(`max(if(data_key = {${keyParam}:String} and data_type = ${dataType} and ${condition}, 1, 0)) = 1`);
...
sql: `and website_event.event_id in (
  select event_id from event_data
  where website_id = {websiteId:UUID} and created_at between ...
    and data_key in (${keyRefs.join(', ')})
  group by event_id having ${clauses.join(' and ')})`
// Session properties instead: tuple(website_id, session_id) IN (select ... from session_data final)
```

**Flow:** parsePropertyFilters (params.ts) decodes `epf0=2.re.someProp.value` wire format → compiler emits an anti-join subquery per group → spliced into filterQuery.
**Invariant:** multi-property AND requires the `group by id having max(if(...))=1` pattern — a plain `IN` per property would OR across rows of the same event. Session variant MUST join on the tuple `(website_id, session_id)` (session ids are only unique per website) and uses `session_data final` for CollapsingMergeTree dedup.
**Probe:** round-trip tests `src/lib/params.test.ts:10-75` pin the epf/spf encode/parse incl. malformed rejection (:36, :64).
**Probe:** `grep -c "max(if(data_key" src/lib/clickhouse.ts` → 2; `grep -c "session_data final" src/lib/clickhouse.ts` → ≥2 lines.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "getEventPropertyFilterQuery getSessionPropertyFilterQuery having", limit: 10 });
```

## Verdict
Adopt group-having anti-joins for EAV-style filtering in column stores; adapt param naming and data-type columns to your schema; keep the tuple-join invariant if ids are website-scoped.
