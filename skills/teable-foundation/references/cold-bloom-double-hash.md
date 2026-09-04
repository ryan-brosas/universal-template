<!-- capsule-v2 -->
**Source:** teable `part-codec.ts` bloom section @ pin `06a4461e`
**Question:** How does a per-part record-id bloom filter prune downloads safely?
**Path/Symbol:** `IRecordBloom {m,k,b64}`, `buildRecordBloom(recordIds, count)`, `bloomMightContain(bloom, recordId)`, `fnv1a(value, seed)`, `bloomBitPositions`
**Signature:** double hashing `(h1 + i*h2) % m` with k=7 hashes, 10 bits/element (~0.8% FPR), min 64 bits; bit array stored base64 inside `_stats.json` entries (`recordBloom?`).
**Data Shape:** h1=FNV-1a seed 0; h2=FNV-1a seed 0x9e3779b9 forced ODD.
**Decisive source:** :386-396 — "// odd step so all bits stay reachable; `| 1` alone would coerce to a SIGNED 32-bit int (negative for hashes ≥ 2^31), making the modulo negative and the buffer write a silent out-of-range no-op — a false-negative factory" then `const h2 = (fnv1a(value, 0x9e3779b9) | 1) >>> 0`. Both operands kept non-negative < 2^53 so `%` stays in [0,m). fnv1a uses `Math.imul(...) >>> 0` per round.
**Flow/Invariant:** Bloom answers are advisory-negative-only: `false` means DEFINITELY absent → prune; `true` scans anyway. Reader consults it only when stats carry an entry AND the query has a recordId (`statsAllowPart`). Writer builds it from the input's distinct recordIds — record-major sorted input means boundaries suffice to collect them (`part.recordIds.push` only on change).
**Probe (direct test):** spec "record bloom / never yields false negatives and prunes most foreign ids" asserts all 61 real ids contained and <15/300 foreign false positives; live: `grep -cF '(fnv1a(value, 0x9e3779b9) | 1) >>> 0' apps/nestjs-backend/src/features/record-history-cold/part-codec.ts` → `1`; `grep -oE 'BLOOM_HASHES = [0-9]+' ...` → `7`.
**Retrieve:** `echo '{"project":"teable","pattern":"buildRecordBloom","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — the signed-int modulo trap generalizes to ANY JS bit-array/hash-bucket code.
