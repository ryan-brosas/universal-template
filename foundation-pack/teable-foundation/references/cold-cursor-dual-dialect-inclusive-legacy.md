<!-- capsule-v2 -->
**Source:** teable `record-history-cold-read.service.ts` cursors @ pin `06a4461e`
**Question:** How do cold cursors coexist with legacy Prisma id cursors across the buffer/S3 seam?
**Path/Symbol:** `CURSOR_PREFIX='chs1:'`, `encodeColdCursor(createdTime, id)`, `decodeColdCursor(cursor)`, `resolveBoundary`, IBoundary {t, id, inclusive}
**Signature:** cold cursor = `'chs1:' + base64url(JSON {t, id})` → boundary inclusive:false (next page strictly after). Legacy cursor = bare row id → findUnique in buffer; found → INCLUSIVE boundary at that row ("legacy prisma cursors point at the next row to return"); NOT found (already flushed out) → warn + restart page.
**Data Shape:** decode failures return undefined (never throw) so callers treat them as legacy ids.
**Decisive source:** :218-224 — buffer reads use raw SQL with `id COLLATE "C"` so tie ordering (rows sharing created_time) is plain BYTE order — "the same total order the cold-part comparator uses in JS. The db column collation would order mixed-case cuids differently and make pagination unstable across the buffer/S3 seam." Boundary predicate `(created_time < $t OR (created_time = $t AND id COLLATE "C" <=/< $id))`.
**Flow/Invariant:** One total order across both stores makes pagination stable; the two inclusivity dialects are load-bearing and must never be normalized together. Buffer batch loop advances with exclusive boundaries after each fetch.
**Probe (direct test):** spec "cursor codec round-trips and rejects legacy cursors" (`decodeColdCursor('rhlegacy...') === undefined`) and "honors legacy prisma cursors inclusively when the row is still buffered" (page starts AT rhz2); live: `grep -c 'COLLATE' apps/nestjs-backend/src/features/record-history-cold/record-history-cold-read.service.ts` → `3`; `grep -cF "CURSOR_PREFIX = 'chs1:'" ...` → `1`.
**Retrieve:** `echo '{"project":"teable","pattern":"decodeColdCursor","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — COLLATE "C" tie-order is the keystone invariant.
