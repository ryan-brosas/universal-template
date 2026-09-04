<!-- capsule-v2 -->
# System-table rules + orphaned link-storage GC — what makes a physical table a valid teable table, and how are FK leftovers from dead links reclaimed?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Which system columns/constraints/defaults must every data table satisfy, and how does integrity tooling distinguish live link storage from orphaned storage without a registry?

## createSystemTableRules + OrphanedLinkStorageRule
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/table/SystemTableRules.ts` — `createSystemTableRules` (:727–784), `OrphanedLinkStorageRule` (:613–680), `collectActiveLinkStorageRefs` (:217–243) with promise-cache (:131–152), `createOrphanedLinkStorageRepairStatement` (:303–345), `createAutoNumberDefaultStatements` (:682–702).
**Signature:** `createSystemTableRules(): ReadonlyArray<ISchemaRule>` under pseudo fieldId `__system__`; columns: `__id text NOT NULL + unique idx`, `__auto_number integer PK + sequence default`, `__created_time/__last_modified_time timestamptz (created NOT NULL, default now())`, `__created_by/__last_modified_by text (created NOT NULL)`, `__version integer NOT NULL`.
**Data Shape:** active-ref key = `${schema}\0${tableName}\0${columnName}` (NUL-delimited); cache value = per-schema PROMISE of `Set<refKey>|undefined` stored in checker/repairer sessionCache.

### Decisive source
```sql
-- ownership heuristic instead of a registry: junction_* tables or __fk_* columns
-- referencing this table's __id, MINUS the set of refs still declared by live fields
where c.contype='f' and parent=target.__id and single-column fk
→ isLinkStorage = child_table LIKE 'junction_%' OR child_column LIKE '\_\_fk\_%'
→ orphaned = isLinkStorage AND refKey NOT IN activeRefs
```

**Flow:** isValid loads ALL live link fields' storage locations from meta (`field.options->>fkHostTableName/selfKeyName/foreignKeyName where type='link' AND deleted_time IS NULL AND is_lookup IS NULL`) — tolerating missing `field` table by returning undefined (=valid); caches per-schema results as promises in sessionCache so one base-integrity run pays ONE meta scan; compares against pg_constraint-derived single-col FKs; repair execute() drops whole orphaned junction tables (dedup via droppedTables set) else drops just the orphan column, re-resolving refs WITHOUT cache. AutoNumber default repair creates sequence, OWNED BY column, sets nextval default, then setval(MAX(existing),1).
**Invariant:** absence of the meta table degrades to "no orphans" (fail-open check, not crash); a junction table shared with ANY live ref is never dropped even when one constraint looks stale; SystemDefaultRule matches default EXPRESSION fragments case/space-normalized ('now()' or 'current_timestamp') rather than exact strings.
**Probe:** graph probe: search_graph 'OrphanedLinkStorageRule collectActiveLinkStorageRefs'; source pins SystemTableRules.ts :135–152 (promise cache), :303–345 (repair statement); no dedicated spec file — coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "OrphanedLinkStorageRule ACTIVE_LINK_STORAGE_REFS_CACHE_KEY createAutoNumberDefaultStatements", limit: 10 });
```

## Verdict
Adopt the convention-based orphan detection (prefix heuristics + live-field diffing), promise-per-schema session caching, drop-table-vs-drop-column repair split, and fragment-matching default validation; adapt prefixes/column inventory to host schema; omit sequence details if host has no auto-number concept.
