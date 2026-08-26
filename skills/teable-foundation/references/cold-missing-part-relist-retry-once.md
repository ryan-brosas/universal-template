<!-- capsule-v2 -->
**Source:** teable `record-history-cold-read.service.ts` collectMonth + consumer @ pin `06a4461e`
**Question:** What happens when a listed part vanishes mid-read under a concurrent rewrite?
**Path/Symbol:** `ColdSegmentIterator.collectMonth`, `isMissingPartError`, re-list retry
**Signature:** error signature regex `/NoSuchKey|NotFound|ENOENT|does not exist|404/i` over `${name} ${code} ${message}`.
**Decisive source:** :401-406 — "a key from our listing can vanish mid-read when a flusher/compactor heal pass supersedes it — the replacement part exists but is invisible to our stale listing. One fresh re-list + rescan resolves the race; a second miss (or one during the retry) propagates." collectMonth wraps collectMonthOnce in try/catch → single retry after warn log.
**Flow/Invariant:** Exactly ONE retry per month (bounded); the replacement part is found by RE-LISTING (not by guessing keys). Pairs with run-token collision-free writes: concurrent writers never overwrite each other's keys, so duplication (never loss) is the transient state and read-side id-dedup absorbs it.
**Probe (direct test):** `grep -c 'NoSuchKey|NotFound|ENOENT|does not exist|404' apps/nestjs-backend/src/features/record-history-cold/record-history-cold-read.service.ts` → `1`; `grep -c 'collectMonthOnce(yyyymm)' ...` → `2` (initial call + single retry).
**Retrieve:** `echo '{"project":"teable","pattern":"collectMonth","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — stale-listing race handling pairs with the writer's run tokens.
