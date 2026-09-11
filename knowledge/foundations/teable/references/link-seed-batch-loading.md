<!-- capsule-v2 -->
# Link seed batch loading — how does bulk delete collect every linked record id with O(linkFields) queries instead of O(records × linkFields)?

## one query per link field shaped by relationship; pre-init all ids to []; 42P01-tolerant
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `loadExistingLinkRecordIdsBatch(db, tableName, recordIds, field, logger)` (:4387–4523); comment "This reduces O(records × linkFields) queries to O(linkFields) queries" (:4385); consumption in deleteMany :3151–3177. Companion capsules: `missing-host-table-tolerance`, `link-mutation-routing`.
**Signature:** `(db, tableName, recordIds, field: core.LinkField, logger): Promise<Result<Map<recordId, string[]>, DomainError>>`.

### Decisive source
```ts
for (const recordId of recordIds) result.set(recordId, []);        // EVERY id present, even w/o links
// manyMany | oneMany+oneWay: junction SELECT selfKey AS self_key, foreignKey AS foreign_key WHERE selfKey IN (ids)
// manyOne  | oneOne:          own-table SELECT __id AS record_id, foreignKey AS foreign_key WHERE __id IN (ids) → result[id]=[fk] (SINGLE)
// oneMany (two-way):          foreign SELECT selfKey AS self_key, __id AS foreign_key WHERE selfKey IN (ids)
```

**Flow:** per link field, choose the host+columns by relationship exactly as the mutation router does → run ONE grouped query for all dying records → fold rows into the map, appending for multi-value shapes, overwriting with a singleton for FK-on-self shapes.
**Invariant:** THREE details porters break: (1) Pre-initializing every requested id to `[]` is load-bearing — downstream `allLinkedIds.includes` dedup (:3162–3169) and seed merging rely on total keys, and callers can't distinguish "no links" from "not queried". (2) manyOne/oneOne OVERWRITE (`result.set(recordId,[foreignKey])`) because those relationships are single-valued by definition; junction shapes APPEND. Mixing these corrupts seeds. (3) The batch shape change (from per-record to per-field queries) only pays off because `WHERE key IN (…all dying ids…)` uses the index once; porters who re-add per-record loops inside the fold regress to the original N×M cost this function exists to kill.
**Probe:** deterministic grep :4398 (pre-init), :4448–4469 (singleton branch). Delete suites exercise via :574ff.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "loadExistingLinkRecordIdsBatch", limit: 5 });
```
## Verdict
Adopt whenever bulk operations must witness existing relations: relationship-keyed single query per field, total-domain result maps, value-shape-specific folding.
