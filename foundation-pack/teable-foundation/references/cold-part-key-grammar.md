<!-- capsule-v2 -->
**Source:** teable `apps/nestjs-backend/src/features/record-history-cold/part-codec.ts` @ pin `06a4461e`
**Question:** How are cold-part object keys built and parsed so listing/pruning/healing all agree?
**Path/Symbol:** `buildPartKey`, `parsePartKey`, `PART_FILE_RE`, `padSeq`, `coldRootDir`, `monthPrefix`, `statsKey`, `bucketOfDate`, `bucketId`
**Signature:** `{root}/v1/{tableId}/{yyyymm}/{dd|m}-p{seq4}-{r{runToken}-}?{minRecordId}.ndjson.{zst|gz}`; seq zero-padded to 4.
**Data Shape:** `IParsedPartKey { tableId, yyyymm, kind: 'day'|'month', dd?, seq, minRecordId, compression: 'zstd'|'gzip', key }`; regex `/^(m|\d{2})-p(\d+)-(?:r[a-z0-9]+-)?(.+)\.ndjson\.(zst|gz)$/` — the run-token group is OPTIONAL and non-capturing so pre-token keys still parse (:170-172).
**Decisive source:** :152-168 buildPartKey embeds a random per-writer run token: "two runs computing the same startSeq from the same listing still produce distinct keys, so neither can overwrite (or verification-cleanup-delete) the other's part; read-side id-dedup absorbs the duplication".
**Flow/Invariant:** minRecordId lives IN THE KEY because it powers record-level part pruning on the read path (`part.minRecordId <= recordId`). Parsing requires exactly 3 path segments under the version root + 6-digit month or returns undefined — `_stats.json` deliberately fails to parse. Buckets: day parts carry `dd`, month parts lead with literal `m`; `bucketId()` renders them `yyyymm/dd` vs `yyyymm/m`. UTC only (`getUTCFullYear/getUTCMonth/getUTCDate`) — never local time, or bucket boundaries drift across pods.
**Probe (direct test):** spec `record-history-cold.spec.ts` "part key codec / builds and parses day and month keys" pins `07-p0003-recB.ndjson.*` round-trip AND `parsePartKey(ROOT,'.../_stats.json') === undefined`; live: `grep -cE '^const PART_FILE_RE' apps/nestjs-backend/src/features/record-history-cold/part-codec.ts` → `1`.
**Retrieve:** `echo '{"project":"teable","pattern":"parsePartKey","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — key grammar IS the pruning index; a porter who drops minRecordId from the key breaks record queries silently.
