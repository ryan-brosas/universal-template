<!-- capsule-v2 -->
# Best-effort external-calendar sync fan-out — how do you push every save/delete to Google and CalDAV without letting sync outages break booking?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** What is the per-provider sync contract, the id-mirroring rule, and the error posture?

## Synchronization::sync_appointment_saved / deleted
**Path/Symbol:** `application/libraries/Synchronization.php:51` (`sync_appointment_saved`, 51–110), `:118` (`sync_appointment_deleted`, 118–150), `:250` (`remove_appointment_on_provider_change`, 250–269).
**Signature:** `sync_appointment_saved(array $appointment, array $service, array $provider, array $customer, array $settings): void`
**Data Shape:** Provider settings row carries `google_sync` (bool), `google_token` (JSON with `refresh_token`), `caldav_sync` (bool). Appointment mirrors remote ids in `id_google_calendar` / `id_caldav_calendar`.

### Decisive source
```php
// application/libraries/Synchronization.php:61-98 — create-vs-update keyed by mirrored id, then write-back
if ($provider['settings']['google_sync']) {
    if (empty($provider['settings']['google_token'])) { throw new RuntimeException('No google token ...'); }
    $google_token = json_decode($provider['settings']['google_token'], true);
    $this->CI->google_sync->refresh_token($google_token['refresh_token']);
    if (empty($appointment['id_google_calendar'])) {
        $google_event = $this->CI->google_sync->add_appointment($appointment, $provider, $service, $customer, $settings);
        $appointment['id_google_calendar'] = $google_event->getId();
        $this->CI->appointments_model->save($appointment);   // mirror write-back
    } else {
        $this->CI->google_sync->update_appointment($appointment, $provider, $service, $customer, $settings);
    }
}
if ($provider['settings']['caldav_sync']) { /* same shape via caldav_sync->save_appointment */ }
// :99-109 catch(Throwable) → log_message('error') only
```

**Flow:** fired AFTER successful DB save from Calendar/api v1 (`Calendar.php:381`, `Appointments_api_v1.php:265`): refresh token → create-or-update per backend keyed on the mirrored id → persist the new mirror id → CalDAV pass → whole body wrapped in log-and-continue. Deletes skip backends whose mirror id is empty.
**Invariant:** the mirrored id IS the create/update discriminator — losing it duplicates events on every save; the write-back save happens BEFORE the request returns so a crash can't orphan a created event. The blanket try/catch makes sync strictly best-effort: booking succeeds even with dead Google/CalDAV credentials (the token-missing RuntimeException is swallowed by the same catch). Provider reassignment mid-edit is handled by `remove_appointment_on_provider_change`, which deletes the OLD provider's remote event when ids exist — though its own guard compares `$existing_provider_id !== $existing_appointment['id_users_provider']` against an un-refreshed find (:259-262), so callers must invoke it BEFORE mutating provider id (`Calendar.php:349` does).
**Probe:** `grep -c "log_message(" application/libraries/Synchronization.php` (= 8: two per sync method × 4 methods).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "sync_appointment_saved", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt mirror-id-keyed create/update + immediate write-back + swallow-and-log fan-out + delete-on-provider-change ordering; adapt Google/CalDAV clients to your SDKs; omit the stale-comparison quirk rather than inheriting it (document your fix). Direct tests: none upstream.
