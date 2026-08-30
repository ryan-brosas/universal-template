<!-- capsule-v2 -->
**Source:** teable `external-sort.ts` ExternalRowSorter.spill @ pin `06a4461e`
**Question:** Why must the run swap happen BEFORE any await when spilling?
**Path/Symbol:** `ExternalRowSorter.add`, `spill()`, `writeRun`, `pendingSpills`, `spillError`
**Signature:** `const rows = this.run; const bytes = this.runBytes; this.run = []; this.runBytes = 0;` THEN create the tracked write promise (`finally` releases budget charge + removes from pendingSpills), register it, then `await tracked`.
**Decisive source:** :347-355 doc — "The swap happens BEFORE any await: a budget sweep may spill this sorter while its owner is between adds, and a row pushed during the file write must open the next run — landing inside a file whose contents were already sorted would silently break the merge order." Window check :356-361 contains ZERO awaits before the swap.
**Flow/Invariant:** rows added during an in-flight spill land in the NEW run (spec "a row added while a spill is in flight opens the next run" pins both rows emitted exactly once). Failure model: `this.spillError ??= error` records FIRST failure only; every later add()/drainTo() rethrows it — "a failed spill means rows this sorter accepted are gone, so its output is incomplete — the owning table must error out (and skip its buffer delete), not keep feeding a sorter that cannot deliver" (:180-184 poison test).
**Probe (direct test):** `sed -n '356,361p' apps/nestjs-backend/src/features/record-history-cold/external-sort.ts | grep -c await` → `0` (swap precedes any await); `grep -c 'this.spillError ??= error' apps/nestjs-backend/src/features/record-history-cold/external-sort.ts` → `2` (writeRun + mergeGroupToFile).
**Retrieve:** `echo '{"project":"teable","pattern":"pendingSpills","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — sync-swap-before-await is THE invariant for interruptible sorters.
