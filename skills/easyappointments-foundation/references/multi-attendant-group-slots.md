<!-- capsule-v2 -->
# Multi-attendant group-slot loop — how do group services share slots across different services without overbooking?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** When `attendants_number > 1`, how are candidate slots generated and capacity-checked per service?

## consider_multiple_attendants
**Path/Symbol:** `application/libraries/Availability.php:97` (`consider_multiple_attendants`, lines 97–186).
**Signature:** `consider_multiple_attendants(string $date, array $service, array $provider, ?int $exclude_appointment_id = null): array`
**Data Shape:** In: service with `attendants_number`, `duration` (minutes), optional `slot_interval`; provider row. Out: `H:i` strings. Dispatch happens in `get_available_hours` (:70-76): `attendants_number > 1` → this method, else the period-subtraction path.

### Decisive source
```php
// application/libraries/Availability.php:151-182 — two-query gate per slot
while ($slot_end <= $period['end']) {
    $other_service_attendants_number = ...get_other_service_attendants_number($slot_start,$slot_end,$service['id'],$provider['id'],$exclude_appointment_id);
    if ($other_service_attendants_number > 0) { $slot_start->add($interval); $slot_end->add($interval); continue; }
    $appointment_attendants_number = ...get_attendants_number_for_period($slot_start,$slot_end,$service['id'],$provider['id'],$exclude_appointment_id);
    if ($appointment_attendants_number < $service['attendants_number']) {
        $hours[] = $slot_start->format('H:i');
    }
    $slot_start->add($interval); $slot_end->add($interval);
}
```

**Flow:** build ONE period from the working plan (or its exception) → `remove_breaks` → `remove_unavailability_events` twice (own unavailabilities, then blocked periods) → slide a `[start,start+duration]` window by `slot_interval` (default **15**) across each period.
**Invariant:** the two queries partition the check: same-service appointments count toward capacity (`get_attendants_number_for_period` filters `id_services = service.id`), ANY other-service appointment **vetoes the slot outright** (`get_other_service_attendants_number` filters `id_services !=`). A slot is offered only when other-service count is exactly 0 AND same-service count < attendants_number. Porting only one of the two checks silently double-books cross-service.
**Probe:** `grep -c "get_other_service_attendants_number\|get_attendants_number_for_period" application/libraries/Availability.php` (= 2: the two call sites at :153/:168; definitions live in Appointments_model.php :372/:416).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "get_attendants_number_for_period", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the sliding-window + two-query capacity grammar; adapt the per-slot SQL counts to a single grouped overlap query if porting off CI3's chained query builder; omit the legacy duplicate `$this->CI->load->model('secretaries_model')` line (:38-39 loads it twice — harmless upstream artifact). Direct tests: none upstream; probes pin call-site counts.
