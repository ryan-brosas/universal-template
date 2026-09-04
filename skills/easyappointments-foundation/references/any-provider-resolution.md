<!-- capsule-v2 -->
# Any-provider search ladder — how does "any provider" resolve to one concrete provider without double-booking?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How is the `any-provider` sentinel turned into a real assignment, and what is the ranking rule?

## ANY_PROVIDER sentinel + search_any_provider
**Path/Symbol:** `application/config/constants.php:85` (`ANY_PROVIDER = 'any-provider'`), `application/controllers/Booking.php:661` (`search_any_provider`, 661–690), `:603` (`check_datetime_availability`, 603–646).
**Signature:** `search_any_provider(int $service_id, string $date, ?string $hour = null): ?int`
**Data Shape:** Sentinel is the STRING `'any-provider'`, stored in the appointment's `id_users_provider` field until resolution. Returns provider id or null (no provider fits).

### Decisive source
```php
// application/controllers/Booking.php:671-687 — max-available-hours ranking
foreach ($available_providers as $provider) {
    foreach ($provider['services'] as $provider_service_id) {
        if ($provider_service_id == $service_id) {
            $available_hours = $this->availability->get_available_hours($date, $service, $provider);
            if (count($available_hours) > $max_hours_count && (empty($hour) || in_array($hour, $available_hours))) {
                $provider_id = $provider['id'];
                $max_hours_count = count($available_hours);
            }
        }
    }
}
```

**Flow:** `Booking::register` (:439) replaces `$appointment['id_users_provider']` with `check_datetime_availability()`'s result; that method short-circuits on the sentinel → `search_any_provider`; explicit-provider requests instead regenerate hours and require the chosen hour to still be listed.
**Invariant:** ranking = **most remaining free hours wins**, tie broken by iteration order (first-seen), and a provider whose hour list doesn't contain the requested hour is skipped entirely. The strict `>` means later providers never displace an equal-count earlier one — deterministic but order-dependent on `providers_model->get_available_providers(true)` ordering. Porters who use `>=` make the choice unstable across runs.
**Probe:** `bash -c 'grep -c "ANY_PROVIDER" application/controllers/Booking.php'` (= 3 usages :615/:737/:815; string constant defined at constants.php:85).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "search_any_provider", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt sentinel-until-assignment + max-free-hours ranking with strict `>`; adapt the sentinel value/typing to your schema (a nullable column is cleaner); omit the loose `==` service-id comparison quirk only if your ids are guaranteed ints. Direct tests: none upstream.
