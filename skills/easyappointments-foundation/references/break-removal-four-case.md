<!-- capsule-v2 -->
# Break-removal four-case grammar — how do you punch fixed breaks out of a working day in place?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** What is the reusable contract for subtracting fixed breaks (lunch etc.) from period lists, and where does it differ from the appointment splitter?

## remove_breaks / remove_unavailability_events twins
**Path/Symbol:** `application/libraries/Availability.php:199` (`remove_breaks`, 199–250) and `:262` (`remove_unavailability_events`, 262–317).
**Signature:** `remove_breaks(string $date, array $periods, array $breaks): array` / `remove_unavailability_events(array $periods, array $unavailability_events): array`
**Data Shape:** In: periods as DateTime-carrying arrays (`['start'=>DateTime,'end'=>DateTime]`), breaks as `H:i` string pairs, unavailability events as rows with `start_datetime`/`end_datetime`. Out: same period list mutated by reference inside the loop. Both are **public**, called cross-library (multi-attendant path) and re-usable.

### Decisive source
```php
// application/libraries/Availability.php:215-245 — the four overlap cases (identical shape in both methods)
if ($break_start <= $period_start && $break_end >= $period_start && $break_end <= $period_end) {
    // left-overlap → move period start to break end
    $period['start'] = $break_end; continue;
}
if ($break_start >= $period_start && $break_start <= $period_end
    && $break_end >= $period_start && $break_end <= $period_end) {
    // middle → shrink end to break start AND append right fragment
    $period['end'] = $break_start;
    $periods[] = ['start' => $break_end, 'end' => $period_end];
    continue;
}
// right case trims end; "contains period" case also sets start = break_end
```

**Flow:** outer loop over blockers, inner loop over periods **by reference**; each case mutates or appends and `continue`s to the next case check — a single blocker can trigger at most one case per period.
**Invariant:** the appended fragment is iterated too (PHP foreach over `$periods` while appending sees new elements), so chained overlapping breaks still terminate because each pass only shrinks spans. Porters who snapshot the array before the loop lose the chain-handling.
**Probe:** `bash -c 'grep -cE "// (left|middle|right|break contains|Left|Middle|Right|Unavailability contains)" application/libraries/Availability.php'` (= 8 case-comment anchors across the two methods).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "remove_breaks", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the four-case reference-mutation grammar as a pure function; adapt input typing (the twin accepts any `{start_datetime,end_datetime}` rows — blocked periods are fed through the same method); omit nothing else — this is the cleanest seam in the repo. Direct tests: none upstream (deterministic probe pin only).
