# Scheduling and availability

## Choose a booking surface

Return an existing `scheduling_url` or use an [embed](embeds.md) when Calendly
should own the booking UI. Direct booking uses `POST /invitees` and requires a
paid plan, Standard or above; the Free plan receives 403. Account for the
separate booking budgets in [authentication and requests](authentication-and-requests.md).

## Direct booking

1. Resolve the authenticated user/organization and choose a real event type
   using `GET /event_types` or `GET /event_types/{uuid}` (`event_types:read`).
   Inspect duration, hosts, required questions, pooling type and locations.
2. Query `GET /event_type_available_times` with `event_type`, `start_time` and
   `end_time`. The range must not start in the past and may span at most 31 days.
   Use returned slots; do not synthesize one from working hours minus busy time.
   This endpoint does not use ordinary keyset pagination. Group slots expose
   `invitees_remaining`.
3. Confirm the invitee, host/event type, exact date/time in the invitee's IANA
   timezone, answers and location. Convert the chosen instant to UTC; resolve
   DST gaps/overlaps and phrases such as “next Thursday” before writing.
4. Send `POST /invitees` with `scheduled_events:write`. Its required top-level
   fields are `event_type`, `start_time` and `invitee`. Include invitee email,
   IANA timezone, and either full `name` or `first_name` (plus `last_name` where
   appropriate). Do not copy a vendor example that omits the conditional name.
5. Require the documented 201 status and validate the returned resource before
   reporting success; an arbitrary 2xx response is not a booking receipt. Retain
   the invitee and scheduled-event URIs and show the returned `cancel_url` and
   `reschedule_url` only after validation. Normal notifications and workflows run.
   Confirm final state with authenticated reads or verified webhooks as needed.

A shape example for a location-free event type with no required custom questions
follows. The URI and timestamp are placeholders, not an instruction to book;
replace them with an authorized event type and an actually returned slot.

```json
{
  "event_type": "https://api.calendly.com/event_types/EVENT_TYPE_UUID",
  "start_time": "2030-01-15T15:00:00Z",
  "invitee": {
    "name": "Example Invitee",
    "email": "invitee@example.com",
    "timezone": "America/New_York"
  }
}
```

Payload rules that generic examples miss:

- Omit `location` for a location-free type and for `pooling_type: round_robin`.
  Otherwise follow the event type's configured location: include `kind`, and
  `location.location` when invitee input is needed, such as `ask_invitee`,
  `outbound_call`, or a choice of custom/physical locations. `GET /locations`
  with `user` and `locations:read` helps inspect configured host locations.
- Required `questions_and_answers` must match the question's exact case-sensitive
  text and position. `event_guests` allows at most ten email addresses.
- SMS reminders use `invitee.text_reminder_number` when configured; collect a
  valid phone number and the applicable consent, not an inferred contact field.
- If supplying `tracking`, inspect its schema: nullable members can still be
  required. Do not assume an arbitrary partial UTM object satisfies it.

The available-times endpoint declares `availability:read`, while the broad scope
catalog places it under `event_types:read`. A discovery-plus-availability flow
uses both domains, but verify the actual grants for narrower integrations; do
not conceal the discrepancy or claim either scope alone is proven at runtime.

## Recover without duplicate bookings

A returned slot can disappear before booking. On a clear validation/unavailable
response, fetch fresh slots and let the user choose; do not silently substitute
a different time.

The reviewed contract does not document a booking idempotency key. On timeout,
ambiguous 5xx, unexpected success status or malformed success payload, keep the
attempt uncertain rather than immediately repeating POST.
Correlate event type, UTC start, host and invitee using `GET /scheduled_events`
with a narrow time window and `GET /scheduled_events/{uuid}/invitees` with an
email filter. Preserve returned URIs whenever available. Correlation is not a
server uniqueness guarantee: multiple matches need review. If absence cannot be
established, explain uncertainty before asking whether to try again.

## Links, event types and schedule edits

- `POST /scheduling_links` (`scheduling_links:write`) creates a single-use link
  with `max_event_count: 1`, an event-type URI in `owner`, and
  `owner_type: EventType`. Unused links are documented to expire after 90 days.
- `POST /shares` (`shares:write`) customizes an existing one-on-one event type
  once for sharing; omitted fields inherit from the source type. Check the
  period/date and availability-rule requirements rather than merging blindly.
- `POST /event_types` and `PATCH /event_types/{uuid}` (`event_types:write`)
  currently support one-on-one `kind: solo`. Other returned pooling types do not
  imply these writes support round-robin or collective creation.
- `POST /one_off_event_types` is a distinct contract with host, duration and
  `date_setting`; it supports optional co-hosts. Do not confuse a one-off event
  type with an already-booked meeting or a single-use link.
- `GET /user_availability_schedules` and
  `GET /event_type_availability_schedules` expose rules in their schedule
  timezone. `GET /user_busy_times` uses windows of at most **7 days**; external
  busy time only includes calendars selected to check conflicts. A dependency
  failure is not proof that the calendar is free.
- `PATCH /event_type_availability_schedules` takes the event-type URI as the
  `event_type` query parameter, not an appended UUID. Supplying
  `availability_rule.rules` replaces all rules: GET first, modify the full set,
  preserve unaffected rules and timezone, then read back. An admin editing a
  specific user's schedule must include `availability_rule.user`.

## Cancellation, rescheduling and no-shows

`POST /scheduled_events/{uuid}/cancellation` cancels the **event**, including a
group event; it is not an individual group-invitee removal operation. Confirm
the affected meeting/attendees and optional reason before calling it.

There is no direct reschedule endpoint in the reviewed API. Use the invitee's
`reschedule_url`; cancel-and-rebook is not an equivalent atomic operation.
[Webhook reschedule handling](webhooks.md) owns the old/new invitee lifecycle.

`POST /invitee_no_shows` takes an invitee URI;
`GET /invitee_no_shows/{uuid}` reads the marker and
`DELETE /invitee_no_shows/{uuid}` removes it. These change attendance state,
not the booking time.

## Sources

- [Booking flow](https://developer.calendly.com/docs/api-guides/schedule-events-with-ai-agents.md),
  [create invitee contract](https://developer.calendly.com/api-docs/calendly-api/scheduled-events/create-event-invitee.md).
- [Available times](https://developer.calendly.com/api-docs/calendly-api/event-types/list-event-type-available-times.md),
  [31-day change](https://developer.calendly.com/release-notes/2026/7/9.md),
  [busy times](https://developer.calendly.com/api-docs/calendly-api/availability/list-user-busy-times.md),
  [availability replacement](https://developer.calendly.com/api-docs/calendly-api/availability/update-event-type-availability.md).
- [Create event type](https://developer.calendly.com/api-docs/calendly-api/event-types/create-event-type.md),
  [one-off type](https://developer.calendly.com/api-docs/calendly-api/event-types/create-one-off-event-type.md),
  [single-use link](https://developer.calendly.com/api-docs/calendly-api/scheduling-links/create-scheduling-link.md),
  [customized share](https://developer.calendly.com/api-docs/calendly-api/shares/create-share.md),
  [FAQ](https://developer.calendly.com/docs/getting-started/frequently-asked-questions.md).
