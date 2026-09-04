<!-- capsule-v2 -->
**Source:** teable `part-codec.ts` compression negotiation @ pin `06a4461e`
**Question:** How do mixed-node-version fleets negotiate zstd vs gzip for cold parts?
**Path/Symbol:** `zlibWithZstd`, `hasZstd`, `writeZstd()`, `partFileSuffix()`, `createPartCompressor()`, `createPartDecompressor(key)`
**Signature:** zstd detected via duck-typed `typeof zlibWithZstd.createZstdCompress === 'function'` (node >= 22.15); writer prefers zstd level 3 unless env forces gzip; gzip fallback level 6.
**Data Shape:** suffix `.ndjson.zst` vs `.ndjson.gz`; compression is encoded IN THE KEY so readers dispatch per-object.
**Decisive source:** :106-114 — "Reading always handles both formats, but a `.zst` KEY needs a zstd-capable reader — on a fleet with mixed node versions (engines allow >= 22.0), force gzip with BACKEND_RECORD_HISTORY_COLD_COMPRESSION=gzip so every process can read freshly written parts. Checked per call: env files may load after module evaluation."
**Flow/Invariant:** Asymmetric rule: WRITE format is negotiable by env, READ capability is not — `createPartDecompressor` throws `cannot decompress ${key}: node runtime lacks zstd support` when handed a `.zst` without native support (:129-137). Per-call env check, never module-load capture.
**Probe (direct test):** `grep -c 'BACKEND_RECORD_HISTORY_COLD_COMPRESSION' apps/nestjs-backend/src/features/record-history-cold/part-codec.ts` → `2` (one comment + one read); `grep -oE 'node >= [0-9.]+' ...` → `22.15`.
**Retrieve:** `echo '{"project":"teable","pattern":"createPartCompressor","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — the write-negotiable/read-strict asymmetry is the reusable contract for rolling-deploy codec upgrades.
