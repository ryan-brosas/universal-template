# Custom Calendly booking interfaces

Use for a branded booking form or calendar that reads Calendly data instead of
embedding its hosted UI, including “build it now; connect the account later.”
Endpoint contracts stay in [Scheduling](scheduling.md); credentials and scopes
stay in [Authentication and requests](authentication-and-requests.md).

## Separate implementation from activation

When implementation is authorized, a missing booking link, token or account-plan
confirmation need not block coding. Build against the current public contract,
leave account-specific configuration unset, and test with isolated provider
fixtures. Do not guess the host, event URI, duration or available slots. Ask for
account access when it is needed to connect or validate the real workflow, not
as a prerequisite for work that can be completed safely without it.

Keep public submission disabled until the intended account/event, required
access, privacy notice and abuse protections are configured and approved.
Authorized account-setup reads are separate from public activation; permission
to build the feature does not authorize creating test meetings.
Unconfigured production UI should offer an approved contact route, not fake
availability, an editable dead form or a preview that can claim a real booking.
Test data belongs in fixtures, not a public demo switch or production fallback.

For an existing static site, consider a narrow server-side API handler before
migrating the whole application to SSR. Reuse the page and control owners. Keep
secrets in runtime server bindings; a frontend build variable is not a secret.
The deployment runtime, not just the frontend dev server, must route API requests
correctly while preserving static assets and missing-page responses.

## Let Calendly own booking data

- Project only the event fields the interface needs; never proxy the complete
  authenticated response or accept arbitrary provider URLs from the browser.
- Derive duration, questions, requiredness and choices from the configured event.
  Match answers to its question identity, and detect configuration changes before
  sending stale answers. Do not silently omit an unsupported required field,
  payment or location choice; support it deliberately or fail closed.
- Render provider labels and descriptions as text unless reviewed rich-text
  handling is required. Keep internal option markers distinct from legitimate
  provider values, including an actual choice resembling an “Other” sentinel.
- Keep product browsing limits separate from Calendly's endpoint limits. Query
  actual returned instants, display them in the selected IANA zone, distinguish
  repeated DST times, and ignore older responses after date/timezone changes.
  Use [the current endpoint and change notes](sources.md), not remembered limits
  or a search excerpt, when resolving a contract mismatch.

## Confirmation is a state transition, not a status check

Validate the provider receipt and its correspondence to the selected booking
before exposing confirmation, clearing details or enabling management links.
Complete fallible parsing and date formatting before switching the DOM to success.
An invalid timezone in a nominally successful response must not leave “You're
booked” visible after the renderer throws.

Follow [uncertain-write recovery](scheduling.md#recover-without-duplicate-bookings)
for malformed or mismatched responses as well as network failures. Preserve a
clear uncertain state and prevent automatic resubmission; do not infer that no
meeting exists. A one-use bot-verification token prevents its own replay, not a
second business-level booking with a new token after reload.

## Verify separate boundaries

1. Replace external provider calls with contract fixtures while exercising the
   real browser client and server handler together. Cover dynamic questions,
   literal/long text, empty availability, stale-response races, invalid inputs,
   lost slots and preserved details. Check keyboard and responsive states.
2. Inject unexpected success statuses and malformed success payloads. Verify
   that neither backend nor UI announces a booking or retries the mutation.
3. Run the actual deployment runtime in isolation without loading developer
   secrets. Verify unconfigured API errors, no-JavaScript contact access, static
   asset responses and missing-route behavior. An Astro/Vite preview alone does
   not prove Worker or server routing.
4. Test the configured account only with authorization for the intended reads,
   attendees and side effects. Distinguish fixture coverage, local runtime proof,
   live provider confirmation, deployment and Git push in the handoff.

In the source implementation, negative regressions caught an unexpected HTTP
200 being promoted to booking
success and an invalid timezone revealing confirmation before formatting failed.
Both were corrected and retested. Provider effects were simulated; the local
Worker was exercised, but a real Calendly booking and notification delivery were
not verified. This is implementation evidence, not proof of live account access
or measured improvement from the skill itself.
