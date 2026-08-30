<!-- capsule-v2 -->
# Interval-subtraction period splitting — how do you carve booked time out of a provider's day without losing the leftovers?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** When an appointment/break/unavailability overlaps a free period, what are the exact overlap cases and which side of the split survives?

## Working-plan → free-period ladder
**Path/Symbol:** `application/libraries/Availability.php:334` (`Availability::get_available_periods`, lines 334–530).
**Signature:** `get_available_periods(string $date, array $provider, ?int $exclude_appointment_id = null): array`
**Data Shape:** In: date `Y-m-d` (regex-validated `^\d{4}-\d{2}-\d{2}$` else `InvalidArgumentException`), provider row with `settings.working_plan` JSON `{mon:{start,end,breaks:[{start,end}]},...}`, optional exclude id. Out: array of `['start'=>'H:i','end'=>'H:i']` string pairs. Periods are keyed arrays during processing; `array_values()` re-indexes only at return.

### Decisive source
```php
// application/libraries/Availability.php:450-527 — appointment subtraction cases
if ($appointment_start <= $period_start && $appointment_end <= $period_end
    && $appointment_end >= $period_start) {
    // starts before the period and finishes inside → keep the tail
    $period['start'] = $appointment_end->format('H:i');
} elseif ($appointment_start >= $period_start && $appointment_end < $period_end) {
    // fully inside → unset($periods[$index]) and append head+tail fragments
    unset($periods[$index]);
    $periods[] = ['start' => $period_start->format('H:i'), 'end' => $appointment_start->format('H:i')];
    $periods[] = ['start' => $appointment_end->format('H:i'), 'end' => $period_end->format('H:i')];
} elseif ($appointment_start == $period_start && $appointment_end == $period_end) {
    unset($periods[$index]); // whole period blocked
} else { /* right-overlap trims end; superset unsets; disjoint continues */ }
```

**Flow:** merge appointments+unavailabilities+blocked periods into one event list → seed `[plan.start, plan.end]` if the plan has breaks → clip each break to the day bounds and split → subtract every event from every surviving fragment.
**Invariant:** subtraction never widens a period; a fragment shorter than the service duration simply yields no slots downstream. The working-plan exception for the date **replaces** the weekday entry entirely (`array_key_exists($date, $working_plan_exceptions)` checked before `$working_plan[$working_day] ?? null` is used at :375-380) — a porter who merges instead of replacing opens days that were explicitly closed.
**Probe:** `bash -c 'grep -n "unset(\$periods" application/libraries/Availability.php'` (= 4 lines: break-split :443, inside-split :482, exact-equal :494, superset :519 - all in get_available_periods; the remove_breaks twins mutate in place and append instead).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "get_available_periods", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the five-case overlap grammar and the exception-replaces-plan rule verbatim; adapt the `H:i` string-pair representation to your language's interval type; omit the CI3 `db` plumbing around it. Direct tests: none upstream for this class — probe pins are deterministic greps (coverage caveat recorded).
