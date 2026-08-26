<!-- capsule-v2 -->
**Source:** teable `record-history-flusher.service.ts` discovery @ pin `06a4461e`
**Question:** How does discovery find buffered tables and skip idle BYODB dbs without waking them?
**Path/Symbol:** `discoverGroups`, `discoverBindingGroup`, `listBufferedTables`, `filterKnownTables`, IDiscoveredGroup {kind: 'shared'|'byodb', spaceId?, bindingId?, tableIds}
**Signature:** shared db ALWAYS participates (space filter narrows it, never skips — "shared-storage spaces are valid targets too"); each byodb binding first runs a MAIN-DB-only probe: `SELECT max(tm.last_modified_time) FROM table_meta tm JOIN base b ... WHERE b.space_id = $space` vs binding.lastHistoryFlushedAt — no activity since last flush → return undefined BEFORE ever connecting.
**Decisive source:** :405-418 listBufferedTables uses the loose-index-scan CTE (`WITH RECURSIVE distinct_tables AS (SELECT min(table_id) ... UNION ALL SELECT (SELECT min(r.table_id) WHERE r.table_id > d.table_id) ...)`) — "distinct table_id from the buffer at O(#tables × log n)" instead of a full-scan GROUP BY. :371 "no record activity since the last flush: never connect (keeps idle dbs asleep)" — touchTableMeta stamps last_modified_time on every record write keeping this signal fresh.
**Flow/Invariant:** Discovery is table_meta-driven; that's exactly why orphan rows need special handling. Empty-but-awake tenant db still advances its bookmark to cutoff so quiet dbs stay skipped (:396-398).
**Probe (direct test):** `grep -c 'WITH RECURSIVE distinct_tables' apps/nestjs-backend/src/features/record-history-cold/record-history-flusher.service.ts` → `1`.
**Retrieve:** `echo '{"project":"teable","pattern":"listBufferedTables","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — bookmark-probe-then-connect + loose index scan are both portable.
