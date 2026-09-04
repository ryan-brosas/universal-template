<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Postal Foundation

## Use this for
Use when porting a mail-transfer-agent delivery engine or any DB-as-queue background pipeline: claiming work atomically without a broker, batching deliveries over reused SMTP sessions, classifying send outcomes into Sent/SoftFail/HardFail with backoff, suppressing bad recipients, delivering signed webhooks with bounded retries, or running per-customer MySQL message stores beside a Rails control-plane database. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./db-claim-locking.md` — atomic `UPDATE…LIMIT` claim stamps, batch co-claiming by `(batch_key, ip_address_id)`, retry debounce, stale-lock sweep.
- `./worker-process-loop.md` — multi-thread job polling with an exit-pipe interruptible sleep, graceful TERM drain, and pool sizing before threads start.
- `./worker-role-election.md` — single-row DB election: renew → steal-after-idle → create, releasing on shutdown.
- `./dequeuer-guard-chain.md` — StopProcessing exception control flow threading one shared State through initial → single → scope processors.
- `./outgoing-delivery-ladder.md` — ordered pre-send gates, send-limit three-state columns, hard-fail suppression add / success suppression remove.
- `./incoming-route-modes.md` — bounce linking, spam thresholds vs route Quarantine/Fail modes, endpoint-typed sender dispatch, IP re-allocation on retry.
- `./smtp-endpoint-session-reuse.md` — MX/relay resolution, endpoint walking with Auto-SSL downgrade, RSET-based session reset, one retry on connection reset, per-batch `finish`.
- `./send-result-taxonomy.md` — the SendResult contract every sender returns; Net::SMTP exception table; server-busy retry-time parsing; HTTP status classification with 429 bounce suppression.
- `./ssrf-address-guard.md` — resolve → block-if-ANY-bad → family filter → pin `connection.ipaddr`; negative-code error taxonomy for outbound HTTP.
- `./webhook-retry-funnel.md` — event fan-out to enabled webhooks, five-step delivery service, fixed retry ladder with attempt-count give-up, attempt ledger in the message DB.
- `./message-db-per-server.md` — per-server MySQL databases, hand-rolled SQL builder with backtick-doubling identifier escaping, daily raw-message tables with auto-provision retry, slow-query EXPLAIN logging.
- `./connection-pool-reconnect.md` — lost-connection classification discards the socket and retries the block exactly once on a fresh connection.
- `./live-stats-minute-window.md` — minute-keyed upsert that resets counters after a 30-minute gap, capped 60-minute reads.
- `./held-message-expiry.md` — every Held delivery arms `hold_expiry`; a scheduled task mass-cancels expired holds.
- `./smtp-command-state-machine.md` — phase-gated verb dispatch with labeled error counters and two-line CR memory.
- `./proxy-protocol-preauth.md` — deferred banner until a strict one-shot PROXY header sets the client IP.
- `./rcpt-recipient-classification.md` — ordered bounce/route/credential/relay classifier with longest-prefix IP-trust fallback.
- `./smtp-auth-ladder.md` — PLAIN/LOGIN/CRAM-MD5 resolving `org/server` usernames to one session credential.
- `./data-dot-termination.md` — handler-swap body mode: dot-unstuffing, folded header index, two-line CR terminator gate.
- `./finished-terminal-gates.md` — size → self-hop loop → From-identity gates, then per-recipient persistence; reject-and-reset keeps sessions hot.
- `./nio-event-loop.md` — single-selector forked server: monitor-carried clients, STARTTLS socket swap, empty-selector process exit.
- `./dkim-header-canonicalization.md` — how do you produce a relaxed/relaxed DKIM-Signature for arbitrary raw mail without a DKIM library.
- `./dkim-signing-wiring.md` — where in the send pipeline does signing attach, and what key/signer object does it use.
- `./spam-inspector-fleet.md` — how do you fan a message out to rspamd/spamassassin + ClamAV without letting a scanner outage block delivery.

## Capsule map
- **Queue claim plane** — `db-claim-locking`: `locked_by/locked_at/retry_after/attempts` columns + `HasLocking`; claim = one `UPDATE … WHERE unlocked AND ready LIMIT 1` stamped with `(locker, lock_time)` then read back by that exact pair; batch siblings co-claimed under the same stamp keyed by `batch_key + ip_address_id`; `ready_with_delayed_retry` debounces retries 30 s; `TidyQueuedMessagesTask` destroys days-stale locks.
- **Worker runtime** — `worker-process-loop`: N work threads poll JOBS every 5 s while one tasks thread runs scheduled TASKS hourly-ish; shutdown closes an IO pipe so blocking sleeps return instantly; jobs report `work_completed!` for adaptive metrics; pool sized `threads + 3` BEFORE threads spawn.
- **Role election** — `worker-role-election`: `WorkerRole.acquire` returns `:renewed | :stolen | :created | false` from three ordered conditional updates against a UNIQUE role row; idle > 5 min makes the lock stealable; release = delete own row.
- **Processing spine** — `dequeuer-guard-chain`: every gate either passes or calls `create_delivery(status) → remove_from_queue → stop_processing`; `StopProcessing` exceptions are caught by `catch_stops` (false) and always paired with `state.finished` in an `ensure`; scope router HardFails unknown scopes; unexpected errors requeue via `retry_later` plus an Error delivery.
- **Outgoing gates** — `outgoing-delivery-ladder`: domain/rcpt presence → tag promotion → credential/suppression holds → parse → spam inspect/fail → headers → send limits (`exceeded_at/approaching_at` columns as tri-state latch) → send → suppress-after-hard-fail (≥1 HardFail in 24 h) / de-suppress-on-Sent.
- **Incoming gates** — `incoming-route-modes`: bounce messages are linked to originals (`bounce_for_id`) or HardFailed; route modes Accept/Hold/Bounce/Reject decide terminal handling; endpoint type picks SMTP/HTTP/Address sender; retries re-roll `ip_address_id`.
- **SMTP transport** — `smtp-endpoint-session-reuse`: relays override MX override A-fallback; endpoints walked IPv6-first with source-IP family gating; `Auto` ssl_mode downgrades after SSLError; `send_message` recovers ECONNRESET/EPIPE/SSL once via finish→start→retry; State caches one live sender per `(klass, args)` for whole-batch reuse.
- **Outcome contract** — `send-result-taxonomy`: `{type, details, output, secure, connect_error, retry, suppress_bounce, log_id, time}`; SMTPServerBusy/Timeout/etc ⇒ SoftFail(+parsed delay), SMTPFatalError ⇒ HardFail, everything else ⇒ SoftFail retry; HTTP 2xx Sent / 5xx+negative SoftFail / 429 HardFail+suppress_bounce.
- **Outbound safety** — `ssrf-address-guard`: hostname resolved once, ANY blocked address fails closed (defeats mixed-record DNS tricks), unreachable families filtered, chosen IP pinned onto `Net::HTTP#ipaddr=`; failures map to negative codes −4…−1 instead of exceptions.
- **Webhook pipeline** — `webhook-retry-funnel`: `trigger` fans out per matching webhook; delivery = payload → sign+POST(5 s) → record attempt → appreciate result → save-or-destroy; RETRIES {2,3,6,10,15 min} then drop; every attempt logged into the server's message DB.
- **Per-server storage** — `message-db-per-server`: `postal-server-<id>` MySQL schemas selected by fully-qualified identifiers; string-built SQL whose identifiers are backtick-doubling escaped and whose condition keys are injection-neutralized (test-pinned); raw messages split header/body into `raw-YYYY-MM-DD` tables created lazily on `doesn't exist` retry; queries >50 ms get EXPLAIN-logged.
- **Resilient connections** — `connection-pool-reconnect`: mutex stack pool; `lost connection|gone away|not connected` marks the socket dead (never checked back in) and retries the block once; other errors still check the connection in.
- **Minute stats** — `live-stats-minute-window`: `ON DUPLICATE KEY UPDATE count = if(timestamp < now−1800, 1, count+1)` self-heals stale windows; reads capped at 60 minutes and require ≥1 type.
- **Hold lifecycle** — `held-message-expiry`: `create_delivery("Held")` stamps `hold_expiry = now + default_maximum_hold_expiry_days`; ExpireHeldMessages finds expired holds and emits HoldCancelled; manual sends bypass every hold gate.
- **Inbound command plane** — `smtp-command-state-machine`: every verb handler checks `in_state(...)` first and answers illegal transitions with 503 + Prometheus-labeled error counter (never an exception); `MAIL FROM` strips untrusted `AUTH=`; bare-CR lines are logged and remembered one line back.
- **Identity preauth** — `proxy-protocol-preauth`: under proxy protocol the banner waits; one strict `PROXY …` regex in `:preauth` sets `@ip_address` → blocklist check → `:welcome`; malformed ⇒ disconnect (`@finished = true`) + counter.
- **Recipient routing** — `rcpt-recipient-classification`: domain-reserved bounce tokens → route-domain tokens → session credential → route name+domain, else longest-prefix `SMTP-IP` CIDR match with exactly-one recursion retry; suspended/Reject re-checked per branch.
- **Inbound AUTH** — `smtp-auth-ladder`: username is `org[/\/_]server`, resolved before any secret comparison; PLAIN/LOGIN share key-lookup `authenticate`, CRAM-MD5 verifies HMAC-SHA1(credential.key, challenge) across the server's credentials; success sets `@credential.use`.
- **Body capture** — `data-dot-termination`: swap dispatcher for a body proc; un-stuff leading `..`; fold headers into downcased name→values until blank line; terminator requires `.` with CR on current AND previous line; injected Received header seeds loop evidence.
- **Terminal gates** — `finished-terminal-gates`: bytesize vs config MB → >4 self-hostname Received hops ⇒ 550 → credential's From-domain must resolve ⇒ 530 → persist per recipient type into MessageDB; all paths end `transaction_reset; @state = :welcomed`.
- **Server runtime** — `nio-event-loop`: nio4r selector; client rides `monitor.value` through a STARTTLS socket swap that drops plaintext buffers; handshakes resume nonblock; empty-selector ⇒ `Process.exit(0)` graceful drain.
- **DKIM header canonicalization** — `dkim-header-canonicalization`: how do you produce a relaxed/relaxed DKIM-Signature for arbitrary raw mail without a DKIM library.
- **DKIM signing wiring** — `dkim-signing-wiring`: where in the send pipeline does signing attach, and what key/signer object does it use.
- **Spam/virus inspector fleet** — `spam-inspector-fleet`: how do you fan a message out to rspamd/spamassassin + ClamAV without letting a scanner outage block delivery.
## Extending the foundation
Add one `./<seam>.md` capsule per new porting question. Mined pass 2 candidates still open: DKIM signing via `lib/postal/signer.rb`, click/open tracking middleware, spam inspector trio, inbound-server rate limiting (`Postal::Ratel`), FastServer SSL cert loading. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
postal (MIT), `main@d038eaa8c763d3cafa797ccd6f773d53470bd336` (= base_sha); Codebase Memory projects: pass 1 used `ext-postal` (root `$REFERENCE_ROOT/external/postal`, now retired from list_projects); passes 1–2 revalidated against live project `postal` (root `$REFERENCE_ROOT/postal`, branch main@same sha d038eaa8, FULL mode, generation 2026-08-25T20:10:23Z, 2,276 nodes / 6,254 edges; parse_partial = 7 files all SCSS/yaml docs — zero impact on cited Ruby paths; skipped = 0; not_indexed = vendor/fonts/images BY DESIGN).

## Full view (memory graph)
Revalidate `postal` before porting: run `index_status --project postal --verbose`, `check_index_coverage`, `search_graph`, `trace_path`, `get_code_snippet`. Root `$REFERENCE_ROOT/postal`, branch `main@d038eaa8`, 2,276 nodes / 6,254 edges (generation 2026-08-25T20:10:23Z). All paths cited in pass 2 (`app/lib/smtp_server/{client,server}.rb` + 5 client spec files) reported `no_recorded_issue` + `metadata_match` on check_index_coverage at this pin; pass-1 citations were re-pinned from the retired `ext-postal` project to this one at identical HEAD d038eaa8. Direct-test coverage: RSpec suites exist for the dequeuer, claim job, queued_message scopes/batching, SMTPSender, AddressGuard, Postal::HTTP, ConnectionPool, Database escaping, WebhookDeliveryService, WorkerRole, and per-method inbound suites (`spec/lib/smtp_server/client/{auth,data,finished,helo,mail_from,proxy,rcpt_to}_spec.rb`). Known gap: no spec drives `SMTPServer::Server#run_event_loop` directly (recorded in nio-event-loop capsule).

## Boundaries
Adopt the DB-queue claim protocol (atomic stamp + read-back, batch co-claims, retry debounce, stale sweeps), the StopProcessing guard-chain shape, the SendResult taxonomy with parsed retry hints, session-reusing SMTP client with SSL downgrade, SSRF guard with address pinning, fixed-ladder webhook retries with attempt ledgers, per-tenant schema isolation with escaping discipline, the reconnect-once pool, and the inbound phase-gated state machine with its ordered recipient classifier. Adapt Rails/ActiveRecord idioms, MySQL-specific SQL (backticks, `ON DUPLICATE KEY`), the Net::SMTP exception mapping, klogger/Prometheus instrumentation, and config namespaces to your host. Omit the Rails web UI/controllers, ActionMailer notification content, legacy API versioning, DNS-check workflows, and DKIM/tracking/spam-inspection internals (still unmined) unless your target needs them.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`connection-pool-reconnect.md`](./connection-pool-reconnect.md)
- [`data-dot-termination.md`](./data-dot-termination.md)
- [`db-claim-locking.md`](./db-claim-locking.md)
- [`dequeuer-guard-chain.md`](./dequeuer-guard-chain.md)
- [`dkim-header-canonicalization.md`](./dkim-header-canonicalization.md)
- [`dkim-signing-wiring.md`](./dkim-signing-wiring.md)
- [`finished-terminal-gates.md`](./finished-terminal-gates.md)
- [`held-message-expiry.md`](./held-message-expiry.md)
- [`incoming-route-modes.md`](./incoming-route-modes.md)
- [`live-stats-minute-window.md`](./live-stats-minute-window.md)
- [`message-db-per-server.md`](./message-db-per-server.md)
- [`nio-event-loop.md`](./nio-event-loop.md)
- [`outgoing-delivery-ladder.md`](./outgoing-delivery-ladder.md)
- [`proxy-protocol-preauth.md`](./proxy-protocol-preauth.md)
- [`rcpt-recipient-classification.md`](./rcpt-recipient-classification.md)
- [`send-result-taxonomy.md`](./send-result-taxonomy.md)
- [`smtp-auth-ladder.md`](./smtp-auth-ladder.md)
- [`smtp-command-state-machine.md`](./smtp-command-state-machine.md)
- [`smtp-endpoint-session-reuse.md`](./smtp-endpoint-session-reuse.md)
- [`spam-inspector-fleet.md`](./spam-inspector-fleet.md)
- [`ssrf-address-guard.md`](./ssrf-address-guard.md)
- [`webhook-retry-funnel.md`](./webhook-retry-funnel.md)
- [`worker-process-loop.md`](./worker-process-loop.md)
- [`worker-role-election.md`](./worker-role-election.md)
