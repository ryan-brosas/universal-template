<!-- capsule-v2 -->
**Source:** teable `external-sort.ts` merge machinery @ pin `06a4461e`
**Question:** Why is merge fan-in floored at 2 and how does multi-pass merging keep temp files clean on throw?
**Path/Symbol:** `DEFAULT_MERGE_FAN_IN = 16`, `MIN_MERGE_FAN_IN = 2`, constructor clamp, `mergeSpilledRuns(emit)`, `mergeGroupToFile(files)`, `mergeFiles(files)`, `pickMinRow(heads)`
**Signature:** `this.mergeFanIn = Math.max(MIN_MERGE_FAN_IN, mergeFanIn)` — env may set 1; the floor silently repairs it.
**Decisive source:** :22-27 — "a merge must combine at least two runs per pass or the file count never shrinks and the multi-pass loop spins forever — clamp any smaller configured value (env allows 1) up to this floor"; constructor comment ":166 fan-in of 1 would loop forever (a pass of 1->1 never shrinks the count)".
**Flow/Invariant:** while `runFiles.length > fanIn`: slice groups of ≤K, merge each group into a fresh gzip-level-1 temp file, then unlink consumed inputs; `this.runFiles = [...inputs, ...outputs]` DURING the pass so "a throw mid-pass still cleans every temp file up", replaced by outputs after. Final ≤K files stream through `mergeFiles` (one reader per file — callers must respect fan-in), k-way via linear `pickMinRow` over heads with adjacent id-dedup (`lastId`). Early-return/throw closes remaining head iterators in `finally`.
**Probe (direct test):** specs "multi-pass merge stays correct when runs exceed the fan-in" (fan-in 2, 11 runs, cross-run dup deduped) AND "a fan-in of 1 is clamped so the multi-pass merge still converges"; live: `grep -oE 'MIN_MERGE_FAN_IN = [0-9]' apps/nestjs-backend/src/features/record-history-cold/external-sort.ts` → `2`; `grep -c 'Math.max(MIN_MERGE_FAN_IN, mergeFanIn)' ...` → `1`.
**Retrieve:** `echo '{"project":"teable","pattern":"mergeSpilledRuns","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — floor-of-2 convergence guard applies to any bounded-fan-in merger.
