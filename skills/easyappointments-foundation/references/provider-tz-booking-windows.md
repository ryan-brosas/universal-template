<!-- capsule-v2 -->
# Provider-timezone booking-window filters — how do book-advance and future-limit thresholds clamp the slot list?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** Where do "can't book within N minutes" and "can't book beyond M days" apply, and in whose timezone?

## consider_book_advance_timeout + consider_future_booking_limit
**Path/Symbol:** `application/libraries/Availability.php:588` (`consider_book_advance_timeout`, 588–612) and `:625` (`consider_future_booking_limit`, 625–646).
**Signature:** `consider_book_advance_timeout(string $date, array $available_hours, array $provider): array` / `consider_future_booking_limit(string $selected_date, array $available_hours, array $provider): array`
**Data Shape:** Settings via global `setting()` helper: `book_advance_timeout` (minutes, default 0) and `future_booking_limit` (days, default **90**); both sanitized `is_numeric ? max(0,(int)x) : default`. Provider row carries `timezone`.

### Decisive source
```php
// application/libraries/Availability.php:595-605 — advance timeout in provider TZ
$threshold = new DateTime('now', $provider_timezone);
$threshold->modify('+' . $book_advance_timeout . ' minutes');
foreach ($available_hours as $index => $value) {
    $available_hour = new DateTime($date . ' ' . $value, $provider_timezone);
    if ($available_hour->getTimestamp() <= $threshold->getTimestamp()) {
        unset($available_hours[$index]);
    }
}
// :607-611 — re-index AND string-sort before returning
$available_hours = array_values($available_hours);
sort($available_hours, SORT_STRING);
```

**Flow:** `get_available_hours` applies advance-timeout FIRST (:78), then future-limit (:80). Future limit compares midnight-of-selected-date against `now + N days` in provider TZ: threshold < date → return `[]`; threshold > date → keep hours; equal → `[]`.
**Invariant:** all threshold math is in the **provider's** timezone, not UTC — a porter using server time shifts every cutoff by the offset. The strict `<=` on advance timeout means a slot exactly AT now+timeout is dropped. Final output is sorted ascending as strings (`H:i` sorts lexicographically = chronologically for zero-padded 24h).
**Probe:** `grep -n "sort(\$available_hours" application/libraries/Availability.php` (= 1, line :609).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "consider_book_advance_timeout", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt provider-TZ thresholds + terminal ascending sort; adapt the two settings to your config layer keeping the `max(0,…)` clamps (negative settings must not widen windows); omit nothing — this is a complete porting unit. Direct tests: none upstream.
