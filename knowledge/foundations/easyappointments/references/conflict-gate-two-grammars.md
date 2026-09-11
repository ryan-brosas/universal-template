<!-- capsule-v2 -->
# Two overlap grammars + conflict gate — when is a booking rejected for provider conflict, and by whom?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** Which write paths enforce provider double-booking, and why do the availability counter and the save-time check use different overlap predicates?

## has_provider_conflict (save gate) vs get_attendants_number_for_period (slot counting)
**Path/Symbol:** `application/models/Appointments_model.php:724` (`has_provider_conflict`, 724–746) and `:372` (`get_attendants_number_for_period`, 372–402).
**Signature:** `has_provider_conflict(int $provider_id, string $start_datetime, string $end_datetime, ?int $exclude_appointment_id = null): bool`
**Data Shape:** Both take raw `Y-m-d H:i:s` strings/DateTimes; both honor `exclude_appointment_id` via `id !=` for update-mode self-exclusion.

### Decisive source
```php
// application/models/Appointments_model.php:736-745 — the canonical overlap predicate
// An overlap occurs when:  (existing_start < new_end) AND (existing_end > new_start)
return $this->db
    ->group_start()
    ->where('start_datetime <', $end_datetime)
    ->where('end_datetime >', $start_datetime)
    ->group_end()
    ->get()
    ->num_rows() > 0;
```
vs. the slot counter's **boundary-shifted** pair (:388-393): `(start <= slot_start AND end > slot_start) OR (start < slot_end AND end >= slot_end)` — touching intervals count as overlapping here but NOT in `has_provider_conflict`.

**Flow:** UI path `Calendar::save_appointment` (`application/controllers/Calendar.php:332`) calls `has_provider_conflict` with the exclude id; on hit and no `$force_save` it returns a structured `{success:false, conflict:true}` JSON instead of an exception (:340-346). Public path `Booking::register` re-runs full availability at :439 via `check_datetime_availability()` (`application/controllers/Booking.php:603-646`), comparing the chosen `H:i` against freshly generated hours.
**Invariant:** **API v1 has no conflict gate**: `Appointments_api_v1::store` (`application/controllers/api/v1/Appointments_api_v1.php:208-235`) decodes, derives `end_datetime` from service duration when absent (`calculate_end_datetime`, model :703), saves and notifies — never calling `has_provider_conflict`. A porter must decide explicitly whether their API layer inherits this permissiveness (admin-trust model) or adds the gate.
**Probe:** `grep -rn "has_provider_conflict" application/controllers | wc -l` (= 1 call site: Calendar.php:332).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "has_provider_conflict", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the strict half-open predicate `(start < end') AND (end > start')` as the save-time gate and the boundary-inclusive twin only for capacity counting; adapt the JSON conflict response shape; omit nothing else. Coverage caveat: behavior difference between API/UI paths verified by direct source read, not tests (none exist upstream).
