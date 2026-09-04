<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Rallly: scheduling-poll foundation

## Use this for
Use when porting group-scheduling poll machinery — floating vs timezone-pinned option storage, auto-close/reopen ladders, guest edit-token authorization, vote aggregation and scoring, atomic booking with invite dedup, cron housekeeping (inactivity retention + purge), or per-recipient email rendering. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./floating-all-day-options.md` — how are date-only options encoded so they never shift across timezones?
- `./booking-scheduled-event-times.md` — when is a booked option an all-day UTC-midnight span vs a timed instant?
- `./poll-lifecycle-close-reopen.md` — when does a poll close itself, reopen, and why must manual closes stick?
- `./inactivity-retention-ladder.md` — how do polls get deleted without ever losing active ones?
- `./soft-delete-invisibility.md` — what does "deleted" mean for polls, participants, and votes?
- `./guest-edit-token-actors.md` — how do anonymous participants keep editing their own responses?
- `./participant-visibility-ladder.md` — what does hideParticipants actually hide, per viewer?
- `./score-formula-top-choice.md` — how are winning options ranked and what makes a "top choice"?
- `./booking-transaction-invites.md` — how does a poll option become a scheduled event with deduped invites?
- `./upcoming-past-predicate.md` — how do all-day and timed events split "upcoming" without drift?
- `./email-datetime-rendering.md` — which timezone does each recipient's event email use?
- `./calendar-date-encoding.md` — how do you get a zone's YYYY-MM-DD without trusting locale patterns?
- `./client-option-display-zones.md` — how does one renderer show tz-pinned, floating, and all-day options correctly?
- `./content-moderation-funnel.md` — how is user-generated text gated from regex to AI to verdict?
- `./procedure-access-ladder.md` — which tRPC procedure guards each mutation tier, and where does self-hosting bypass paywalls?
- `./membership-gating.md` — when is space membership "effective" and what do guests get to keep?
- `./housekeeping-cron-routes.md` — how are cron jobs exposed and bounded safely?
- `./rsvp-atomic-registration.md` — how is duplicate registration rejected without a check-then-insert race?
- `./deferred-email-dispatch.md` — why does every side-effectful mutation send mail through after()?
- `./vote-write-path.md` — how are vote updates made safe against stale option ids and activity detection?
- `./notification-preference-jsonb-merge.md` — how do concurrent preference toggles avoid clobbering each other's key?
- `./activity-event-prefs-codec.md` — what does a reader get when stored notification prefs are corrupt or legacy-shaped?
- `./notification-recipient-gate-ladder.md` — in what order are creator-notification suppressions checked, and who is silently skipped?
- `./poll-mute-owner-scoped-toggle.md` — how is ownership enforced on a boolean flip without a check-then-update race?
- `./safe-action-procedure-ladder.md` — where does the second mutation framework live and why does session revocation differ from tRPC?
- `./safe-action-error-code-projection.md` — how does the client turn string server codes into localized feedback safely?
- `./footer-href-url-parse-gate.md` — how do you validate an admin-supplied href so `javascript:` can never survive into an anchor?
- `./footer-links-drop-on-read-roundtrip.md` — what happens when stored footer JSONB was edited outside the app?
- `./singleton-tag-cache-store.md` — how is a one-row global config cached, invalidated, and defaulted when the row is missing?
- `./update-status-fail-soft-ladder.md` — how do you ask an update server "is anything newer?" so hangs, lies, and outages never break the UI?
- `./version-compare-prerelease-blind.md` — how do you compare semver-ish versions without a library, and what must callers guard?
- `./asset-swap-persist-then-delete.md` — how do you swap a stored blob reference without orphaning objects or deleting a just-made-current one?
- `./oauth-pkce-cookie-state-machine.md` — how do you carry OAuth state across a cross-site redirect without a server-side session?
- `./encrypted-oauth-credential-store.md` — how do you keep third-party tokens at rest so a DB leak does not hand out working tokens?
- `./provider-calendar-sync-delete-detection.md` — how do you mirror a provider's resource list so deletions propagate but user choices survive?
- `./orphaned-anonymous-user-reaper.md` — how do you bulk-delete rows whose blast radius is schema-defined, unattended, without destroying someone's data?
- `./license-fetch-failure-classification.md` — how do you tell an operator why an outbound HTTPS call died behind a corporate proxy?

## Capsule map
- **Option encoding** — `floating-all-day-options`: falsy poll.timeZone is the single floating flag; date-only options store UTC midnight with duration 0, timed options pin the poll's zone with minute-durations.
- **Event booking times** — `booking-scheduled-event-times`: duration>0 keeps start+zone; duration 0 snaps to `[UTC midnight, +24h)` with timeZone null, guarding already-correct rows via `% DAY_MS === 0`.
- **Close/reopen ladder** — `poll-lifecycle-close-reopen`: raw-SQL auto-close treats all-day as 24h; only closedReason 'auto' reopens when new future options land; manual closes stick; closing never touches updated_at.
- **Inactivity retention** — `inactivity-retention-ladder`: one updateMany requires 30-day-past dates AND no edits/votes/comments in 30 days AND non-pro space; explicit updatedAt bump on vote writes because empty Prisma data skips @updatedAt.
- **Soft-delete invisibility** — `soft-delete-invisibility`: deleted polls 404 for everyone incl. owner before any payload leaves; aggregates filter participant.deleted so removed voters don't skew scores.
- **Guest token actors** — `guest-edit-token-actors`: resolveActor precedence token→session→UNAUTHORIZED; tokens are TTL=0 and can never elevate to admin or unlock others' notes.
- **Participant visibility** — `participant-visibility-ladder`: server-side strip ladder — notes to host+author only; hideParticipants anonymizes identities but never votes.
- **Score formula** — `score-formula-top-choice`: score=(yes+ifNeedBe)*1000+yes ranks availability-first with yes tiebreak; valid only under MAX_PARTICIPANTS=1000; client mirrors it seeded at 1.
- **Booking transaction** — `booking-transaction-invites`: event+poll-flip in one transaction; participants collapse per lowercased email keeping the most committal vote (accepted>tentative>declined).
- **Upcoming/past predicate** — `upcoming-past-predicate`: dual-arm where clause flips gt/lte together so past ≡ ¬upcoming for both timed (`end>now`) and all-day (`end>todayUtcMidnight`) rows.
- **Email datetime rendering** — `email-datetime-rendering`: all-day renders UTC for everyone; fixed events render invitee-zone-first with zone name; floating events show stored wall time zoneless.
- **Calendar-date encoding** — `calendar-date-encoding`: formatToParts date extraction (no locale pattern trust) + `T00:00:00Z` re-encoding + normalizeTimeZone guard against corrupt zones.
- **Client display zones** — `client-option-display-zones`: fixed instants render viewer-zone, floating wall times read UTC unshifted, all-day always UTC — the exact inverse of the write-side encoding.
- **Moderation funnel** — `content-moderation-funnel`: env-gated cheap-first ladder (banned-domain auto-ban → suspicious-pattern regex → LLM verdict), fail-open everywhere except banned domains, trusted/pro overrides AI flags, verdict travels as data not exceptions.
- **Procedure ladder** — `procedure-access-ladder`: maintenanceGuard→mutationSessionGuard under every procedure; reads trust cookie cache while mutations re-verify the user; possiblyPublic/private/space/pro/spaceOwner tiers with self-hosted bypassing pro gating.
- **Membership gating** — `membership-gating`: one effectiveSpaceMemberWhere predicate (hobby membership = owner-only when billing enabled) applied at EVERY membership resolution; client edit capability freezes purely on poll.status === "open".
- **Housekeeping routes** — `housekeeping-cron-routes`: fail-closed CRON_SECRET bearer guard; external stores deleted before DB rows; per-run caps turn unbounded reaper queues into steady-state drainers.
- **RSVP atomicity** — `rsvp-atomic-registration`: unique (eventId, inviteeEmail) index decides dedup (P2002 → typed already_responded), never a check-then-insert race; locale/timeZone frozen at registration.
- **Deferred email dispatch** — `deferred-email-dispatch`: every send rides after() post-response with catch-log isolation; actor excluded from own notifications; branding + recipient locale resolved fresh at send time.
- **Vote write path** — `vote-write-path`: replace-all-votes in one transaction filtering stale optionIds against current options; explicit updatedAt bump keeps active voters' polls off the retention ladder.
- **Prefs JSONB merge** — `notification-preference-jsonb-merge`: UPDATE-first `prefs || patch::jsonb` so concurrent key toggles can't clobber; create fallback for the cuid, P2002 race re-runs the atomic merge.
- **Event prefs codec** — `activity-event-prefs-codec`: closed-key `{entity}.{sub-entity}.{verb}` taxonomy; safeParse failure (one unknown key invalidates the whole record) silently yields all-on defaults — never throws.
- **Recipient gate ladder** — `notification-recipient-gate-ladder`: poll-probe gates (missing/deleted/self/muted) precede the user fetch; anonymous creator filtered in SQL; per-type pref check last because prefs live on the user row; null = silent no-op.
- **Mute toggle** — `poll-mute-owner-scoped-toggle`: ownership inside updateMany's where clause with count-decided typed `{ok,reason:"notFound"}` outcome; client patches tRPC cache + Undo toast; direct test mutations.test.ts:207–239.
- **Safe-action ladder** — `safe-action-procedure-ladder`: actionClient→authActionClient→adminActionClient mirrors tRPC tiers; all errors collapse to string codes; InvalidSessionError revokes the session inline because server actions CAN write cookies.
- **Error-code projection** — `safe-action-error-code-projection`: useSafeAction always router.refresh()es on success and switch-projects known string codes to localized toasts with a default-first generic fallback.
- **Href scheme gate** — `footer-href-url-parse-gate`: parse with `new URL` and allowlist {http:, https:} — the browser's parser is the single normalization authority that folds `jAvA\tscript:` into one scheme a regex would miss; absolute-only because links must resolve from emails.
- **Footer roundtrip** — `footer-links-drop-on-read-roundtrip`: ONE schema validates at write (action inputSchema) AND per-entry at read (safeParse flatMap drop + re-slice to 5), so out-of-band DB edits can neither inject hrefs nor break the page; cloud reads [] silently but its write action throws FORBIDDEN.
- **Singleton settings store** — `singleton-tag-cache-store`: seeded id:1 row, plain update (no upsert by design), every field null-coalesced so a vanished row degrades to defaults; writers own freshness via one shared tag constant on both unstable_cache and updateTag sides.
- **Update-status ladder** — `update-status-fail-soft-ladder`: four fail-soft null exits (env precheck, non-ok, schema mismatch, throw) + explicit 3s AbortSignal (Node fetch has none) + client-side within-major guard over an all-nullish response schema, because fleet binaries outlive server assumptions.
- **Version compare** — `version-compare-prerelease-blind`: strip v/[-+] suffix then numeric zero-padded component walk (4.9 < 4.10); prerelease sorts equal to its release; getMajorVersion returns null on garbage and callers must guard before isOutdated.
- **Asset swap lifecycle** — `asset-swap-persist-then-delete`: persist DB reference first, after()-delete old object only when different; documented last-write-wins cleanup race accepted until a sign-time Asset table; three features share the one implementation.
- **OAuth PKCE cookie state** — `oauth-pkce-cookie-state-machine`: state+verifier+redirect-to parked in httpOnly cookies with one 10-min TTL; callback trusts query state only compared against the cookie; redirect validated at write AND read via sentinel-origin WHATWG probe; every failure redirects with `error=`, never renders.
- **Encrypted credential store** — `encrypted-oauth-credential-store`: version‖salt‖iv‖tag‖ciphertext base64 envelope (AES-256-GCM, PBKDF2-SHA256 @210k); composite-key upsert so re-auth refreshes in place; load path decrypt→JSON.parse→zod parse fail-loud by design (contrast the lenient prefs codec).
- **Provider sync** — `provider-calendar-sync-delete-detection`: absence from the provider response IS the deletion signal (notIn sweep); dangling default references cleared in the same transaction before rows are marked; upsert create/update field split keeps the user-owned isSelected out of the update arm.
- **Orphaned-guest reaper** — `orphaned-anonymous-user-reaper`: ONE predicate shared by read and delete (session-TTL-window liveness + `{none:{}}` cascade guards); deleteMany re-applies the full filter onto snapshot ids; CI script buckets every User cascade relation guarded vs ignored-with-reason, stale entries fail.
- **License fetch failure** — `license-fetch-failure-classification`: thrown fetch classified timeout / tls (cause.code TLS pattern → NODE_EXTRA_CA_CERTS remedy in the message) / network / verbatim rethrow; only the exact "fetch failed" TypeError counts as transport, so config bugs never wear a connectivity costume.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Rallly (AGPL-3.0), `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory project `rallly` (root `/mnt/hdd/utopia/inspo/rallly`, FULL mode, 26,309 nodes / 48,944 edges, generation 2026-08-25T19:55:51Z, head==base at index time = zero drift; parse_partial ×24 confined to SQL migrations/prisma models/poll-footer.tsx/database client.ts/powered-by.tsx/shared-styles.css — none cited; check_index_coverage on all cited paths: no_recorded_issue + metadata_match).
Pass history: pass 1 (pre-ledger, 20 refs) indexed under the since-retired project `ext-rallly` @ `/mnt/hdd/utopia/inspo/external/rallly`; pass 2 (2026-08-26, FAC-256 dedicated lane) re-established the graph under `rallly` at the canonical root at the SAME commit, reconciled loader/map/provenance to it, and added the notification-plane + safe-action capsules (26 refs); pass 3 (2026-08-26, FAC-256 continuation) deepened the self-host instance-settings admin plane (+6: footer href gate, footer roundtrip, singleton store, update-status ladder, version compare, asset-swap lifecycle — three upstream test suites read directly), zero pin drift re-verified by git before edits. Pass 4 (2026-08-27, dedicated deepening lane) mined the calendar-connection plane, the orphaned-guest reaper, and the licensing failure classifier (+5: oauth-pkce-cookie-state-machine, encrypted-oauth-credential-store, provider-calendar-sync-delete-detection, orphaned-anonymous-user-reaper, license-fetch-failure-classification — licensing mutations.test.ts read directly; Codebase Memory MCP not connected this session, direct source/test reading fallback recorded in verification.md), zero pin drift re-verified by git before edits.

## Full view (memory graph)
Revalidate `rallly` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts (option encoding, scheduled-event-times derivation, upcoming/past predicate, calendar-date helpers, score formula); adapt the tRPC procedure ladder, Prisma transaction shapes, and Hono route shells to your host stack; omit cloud-only product surfaces (Stripe billing flows, PostHog analytics calls, Quick Create gating, white-label licensing) and the landing/docs apps.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`activity-event-prefs-codec.md`](./activity-event-prefs-codec.md)
- [`asset-swap-persist-then-delete.md`](./asset-swap-persist-then-delete.md)
- [`booking-scheduled-event-times.md`](./booking-scheduled-event-times.md)
- [`booking-transaction-invites.md`](./booking-transaction-invites.md)
- [`calendar-date-encoding.md`](./calendar-date-encoding.md)
- [`client-option-display-zones.md`](./client-option-display-zones.md)
- [`content-moderation-funnel.md`](./content-moderation-funnel.md)
- [`deferred-email-dispatch.md`](./deferred-email-dispatch.md)
- [`email-datetime-rendering.md`](./email-datetime-rendering.md)
- [`encrypted-oauth-credential-store.md`](./encrypted-oauth-credential-store.md)
- [`floating-all-day-options.md`](./floating-all-day-options.md)
- [`footer-href-url-parse-gate.md`](./footer-href-url-parse-gate.md)
- [`footer-links-drop-on-read-roundtrip.md`](./footer-links-drop-on-read-roundtrip.md)
- [`guest-edit-token-actors.md`](./guest-edit-token-actors.md)
- [`housekeeping-cron-routes.md`](./housekeeping-cron-routes.md)
- [`inactivity-retention-ladder.md`](./inactivity-retention-ladder.md)
- [`license-fetch-failure-classification.md`](./license-fetch-failure-classification.md)
- [`membership-gating.md`](./membership-gating.md)
- [`notification-preference-jsonb-merge.md`](./notification-preference-jsonb-merge.md)
- [`notification-recipient-gate-ladder.md`](./notification-recipient-gate-ladder.md)
- [`oauth-pkce-cookie-state-machine.md`](./oauth-pkce-cookie-state-machine.md)
- [`orphaned-anonymous-user-reaper.md`](./orphaned-anonymous-user-reaper.md)
- [`participant-visibility-ladder.md`](./participant-visibility-ladder.md)
- [`poll-lifecycle-close-reopen.md`](./poll-lifecycle-close-reopen.md)
- [`poll-mute-owner-scoped-toggle.md`](./poll-mute-owner-scoped-toggle.md)
- [`procedure-access-ladder.md`](./procedure-access-ladder.md)
- [`provider-calendar-sync-delete-detection.md`](./provider-calendar-sync-delete-detection.md)
- [`rsvp-atomic-registration.md`](./rsvp-atomic-registration.md)
- [`safe-action-error-code-projection.md`](./safe-action-error-code-projection.md)
- [`safe-action-procedure-ladder.md`](./safe-action-procedure-ladder.md)
- [`score-formula-top-choice.md`](./score-formula-top-choice.md)
- [`singleton-tag-cache-store.md`](./singleton-tag-cache-store.md)
- [`soft-delete-invisibility.md`](./soft-delete-invisibility.md)
- [`upcoming-past-predicate.md`](./upcoming-past-predicate.md)
- [`update-status-fail-soft-ladder.md`](./update-status-fail-soft-ladder.md)
- [`version-compare-prerelease-blind.md`](./version-compare-prerelease-blind.md)
- [`vote-write-path.md`](./vote-write-path.md)
