---
name: freescout-foundation
description: "Use when porting helpdesk email pipelines: IMAP fetch paging with count-driven pagination, hash-witnessed Message-ID threading, reply-separation ladders, bounce detection, per-mailbox SMTP driver swaps, schedule self-healing supervisors, deferred notification buses, and SSRF-guarded URL imports."
disable-model-invocation: true
---

# FreeScout Foundation

## Use this for
Use when building or porting an email-driven ticketing backend: fetching mail into conversations, threading replies across rewritten Message-IDs, separating quoted replies, sending outbound agent replies with retry/idempotence, multi-mailbox SMTP switching under one worker, cron self-healing, notification fan-out with undo windows, presence indicators without websockets, and URL-import hardening. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/imap-fetch-paging.md` — count-driven pagination so short pages can't silently drop the newest mail; charset latch; connection backoff.
- `references/messageid-threading-ladder.md` — In-Reply-To → References → body-marker candidate walk with app-key hash witnesses; cross-mailbox re-import flip.
- `references/reply-separation-ladder.md` — shortest-candidate-wins quote cutting; Proton/Yahoo/Outlook quirk overrides; hashed separator mode.
- `references/bounce-detection-ladder.md` — four-signal DSN detection and cross-conversation bounced-thread write-back.
- `references/conversation-writein-ladder.md` — customer-email field mutations: spam freeze, deleted revive, monotonic has_attachments, folder placement predicate.
- `references/thread-observer-denormalization.md` — exclusion-list predicates keeping threads_count/preview/read_by_user consistent.
- `references/outbound-reply-job.md` — 5-min→hourly release ladder, accepted-status idempotence gate, 1500-char References trim keeping first+last.
- `references/mail-driver-swap.md` — content-hash-guarded mailer rebuild for per-mailbox SMTP/OAuth inside one worker.
- `references/schedule-selfhealing.md` — expiresAt mutexes, cached mutex names, ps-scan killers, orphaned-mutex GC.
- `references/deferred-notification-bus.md` — static event ledger flushed on terminate + 15 s undo-window delay; actor self-notification removal.
- `references/auto-reply-loop-guard.md` — responder-header filter plus SendLog-count ceiling that provably ends vacation-responder wars.
- `references/folder-counter-coalescing.md` — cache-lock dispatch dedupe, per-folder-type counting predicates, hourly reconciliation sweep.
- `references/conversation-access-ladder.md` — admin→mailbox-membership→only-assigned policy order; global-default/per-user permission resolution.
- `references/conv-viewer-presence.md` — single-key cache heartbeat map with 25 s sweeper TTL and bulk user hydration.
- `references/ssrf-guard.md` — multi-representation host expansion, CIDR blocklist, canonical-IP gate, per-hop redirect revalidation.
- `references/auth-token-webcron-gates.md` — HMAC tokens keyed on password hash (free revocation) and 404-cloaked web cron.
- `references/option-kv-store.md` — sentinel-defaults batch reader and no-write-on-same-value setter for runtime settings.
- `references/forward-as-customer-cid.md` — `@fwd` sender substitution from hostile HTML and CID→URL attachment rewriting with embedded-flag accounting.
- `references/customer-upsert-identity.md` — separate-email-table identity with orphan healing; side-effectful CC sanitizer trap.
- `references/messageid-spam-survival.md` — prefix+hash outbound grammar, base64 body marker, SpamAssassin-tested ids.
- `references/mail-var-templating.md` — `{%var,fallback=X%}` grammar with dual-key strtr merge and escape-before-nl2br ordering.
- `references/module-plugin-plane.md` — string-keyed Eventy filter/action API, background-action deferral, crc32-jittered license cron.
- `references/vendor-override-plane.md` — shadow `overrides/` tree replacing vendor classes wholesale; re-diff-on-bump discipline.
- `references/fetch-heartbeat-liveness.md` — success-vs-attempt timestamps, cadence-aware alert threshold, set-before-send alert latch.
- `references/move-forward-lineage.md` — meta-pointer forward lineage with time-boxed parent-reply inheritance and signature history.
- `references/agent-reply-admission.md` — identity/access gates for replies-by-email plus the four-way assignee switch.

## Capsule map
- **Fetch kernel** — `imap-fetch-paging`: SEARCH-COUNT-driven page loop (`ceil(total/page_size)`) replaces count-of-page termination (#4624 newest-mail loss); charset-not-supported ⇒ setCharset(null) latch; 'connection setup failed' ⇒ +500 ms sleep, exactly one retry; POP3 duplicate-entry races swallowed.
- **Threading** — `messageid-threading-ladder`: candidates = [In-Reply-To, References…, base64 `{#FS:…#}` body marker] each also tried as per-mailbox generated variant; notification/reply/auto-reply prefixes carry `md5(thread.app.key)[:16]` witness — mismatch = drop, never trust raw id; duplicate-id in another mailbox with FS-prefix ⇒ `$extra` re-import under artificial id; Jira stem collapse; forwarded-notification subject guard.
- **Quote cutting** — `reply-separation-ladder`: split by every separator (incl. mailbox `before_reply`, optional `regex:` entries), keep candidates with real text above the cut, return SHORTEST; user-to-notification mode narrows to `fsNotifReplyAbove` marker and strips Outlook `divRplyFwdMsg`; `alternative_reply_separation` switches to keyed-hash separator only.
- **Bounces** — `bounce-detection-ladder`: attachment delivery-status content-type OR multipart/report+report-type headers OR mailer-daemon@ From OR empty Return-Path; first hit wins; original thread recovered from embedded message/rfc822 Message-ID via prefix grammar; SendLog DELIVERY_ERROR + bidirectional bounced_by_* status data.
- **Conversation write-in** — `conversation-writein-ladder`: status→ACTIVE unless spam (#5005), deleted state revived to PUBLISHED, `setLastReplyAt` waiting-since semantics switch, BCC preserved from first email, has_attachments monotone, thread-save failure deletes a just-created conversation forever, updateFolder precedence draft>deleted>spam>closed>assigned>unassigned.
- **Denormalization** — `thread-observer-denormalization`: observer bumps threads_count (customer/message published only), user_updated_at (non-customer), preview (non-forward), read_by_user reset when conversation born from customer; realtime refresh only for customer threads and drafts.
- **Outbound** — `outbound-reply-job`: tries=168, timeout=120 s vs hung fwrite; attempts==1 → release(300) else release(3600); ≥3 attempts or 5xx ⇒ INTERMEDIATE_ERROR; terminal SEND_ERROR only through fail(); ACCEPTED-status early-return makes retries idempotent; References trimmed to 1500 chars keeping first+last then reversed oldest-first; Outlook Thread-Index passthrough; per-recipient SendLog with Mail::failures().
- **Driver swap** — `mail-driver-swap`: md5(json config) guard → forgetInstance(mailer/swift.mailer/swift.transport) → re-register MailServiceProvider → Mail::swap; OAuth refresh before send with Google r_token carry-forward; post-send RestartSwiftMailer listener frees Swift temp files.
- **Scheduler** — `schedule-selfhealing`: withoutOverlapping(expiresAt=30 min); fetch mutex NAME cached so the next tick can kill pids whose mutex expired; queue:work duplicates restarted-then-killed; stale mutexes force-forgotten only after proving `ps` works; web-cron route allowed as scheduler host.
- **Notifications** — `deferred-notification-bus`: listeners only REGISTER event types onto a static ledger; TerminateHandler (HTTP) / FetchEmails tail (CLI) flush; everything dispatches delayed by UNDO_TIMOUT=15 s on the emails queue; causing-user removed per medium; menu/browser mediums coalesce users uniquely.
- **Auto-reply** — `auto-reply-loop-guard`: gate order imported?→enabled?→autoresponder-headers→bounce→spam→Eventy→SendLog auto_reply count in 180 min (≥10 stop, ≥2 subject-collision check)→internal-mailbox stop; job answers In-Reply-To with FS_autoreply hash id.
- **Counters** — `folder-counter-coalescing`: dispatch deduped by `folder_update_lock_{id}` cache key (5 min TTL), job re-checks and finally-unlocks; TYPE_MINE/STARRED/DELETED/indirect/default counting predicates; active≤total by construction; hourly sweeper heals drift.
- **Access** — `conversation-access-ladder`: isAdmin bypass → pivot-table membership → checkIsOnlyAssigned (assignee OR creator OR unrestricted) ; delete adds PERM_DELETE_CONVERSATIONS bit; permissions resolve global-default-then-per-user override; same ladder guards reply-by-email admission.
- **Presence** — `conv-viewer-presence`: global `conv_view` cache `[conv][user]={t,r}` heartbeated by page JS; every-minute command drops entries idle >25 s, fires RealtimeConvViewFinish + Eventy action; getViewersInfo picks first replying else first viewer, hydrates users in one query.
- **SSRF** — `ssrf-guard`: scheme allowlist; candidate set = literal + hex-decoded + gethostbyname + dns_get_record(A|AAAA) + self-references; CIDR blocklist incl. cloud metadata ranges; env allowlist bypass; isSafeHost rejects any `0x` token and non-inet_pton-canonical IPs; sanitizeRemoteUrl manually follows ≤20 redirects re-checking every hop.
- **Stateless auth** — `auth-token-webcron-gates`: base64(user:expiry:hmac_sha256(user:expiry, app.key+password_hash)) restores sessions only for in-app requests and fails anonymous-silent (password change revokes all); web cron compares secret via hashEquals and 404s on miss, feeding Artisan schedule:run.
- **Settings** — `option-kv-store`: JSON-only values (serialize banned), static per-process memo caching even sentinel-resolved defaults, batch whereIn reader completing from memo when possible, write-skipping setter powering edge-triggered alert latches.
- **Fwd-as-customer** — `forward-as-customer-cid`: gate = subject prefix regex ∧ single To ∧ stripped-body starts `@fwd` ∧ forwarder is existing user; sender extracted after cid:/mailto:/entities/\@ scrubbing; attachments rewritten cid→url with embedded flag persisted; all-embedded undoes has_attachments.
- **Customer identity** — `customer-upsert-identity`: emails in own table → find-or-create customer, heal orphan email rows, never overwrite names on match; fetch creates customers for ALL header participants; Conversation::setCc sanitizer itself parses "Name <email>" and creates customers (trap).
- **Message-ID grammar** — `messageid-spam-survival`: `FS_(notify|reply|autoreply)-<ids>-<hash16>@domain` minted at send time (never stored for user threads), deterministic `FS_conversation-<n>-<md5>` anchor for notification In-Reply-To, base64 body marker survives Gmail linkification, hashed reply separator = separator+md5(msgid.key)[:8]; upstream test asserts zero SpamAssassin MSGID matches.
- **Templating** — `mail-var-templating`: dotted vars with `,fallback=` clause; two-phase scan fills both full-token and bare-token keys; missing+remove_non_replaced strips leftovers; escape=htmlspecialchars then nl2br (nl2br always); strtr single pass; recursion-guarded fromName.
- **Plugins** — `module-plugin-plane`: nwidart Modules tree excluded from core graph but licensed via WpApi JSON API; license cron minute/hour jittered by crc32(app.key) mod 59/23; Helper::backgroundAction defers arbitrary Eventy actions via queued TriggerAction job; filters must return values, actions are void.
- **Overrides** — `vendor-override-plane`: whole-class replacements under `overrides/<vendor>/...` win autoload; graph indexes them as first-class classes (webklex 472 nodes); bump discipline = re-diff every overridden file against upstream.
- **Liveness** — `fetch-heartbeat-liveness`: last_run stamped unconditionally, last_successful_run only on clean pass with mailboxes present; monitor alerts once (latch set BEFORE send) when now-last_success > fetch_schedule*60+period*60, sends recovery mail on latch clear.
- **Move/forward** — `move-forward-lineage`: moves recorded as MOVED_FROM_MAILBOX lineitems carrying new mailbox id; forward child merges parent replies created ≤ fork point; per-reply mailbox_change_history keeps signatures correct; meta keys read through backward-compat map.
- **Agent admission** — `agent-reply-admission`: hasEmail(alternate list) → prev_thread exists → can view conversation; refusals setSeen + courtesy error job; assignee switch ANYONE/REPLYING_UNASSIGNED/REPLYING/KEEP_CURRENT; saved thread To rewritten to customer.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question (candidates: `ParseEml.php` import path, `Helper::iconvMimeDecode` encoding ladder, `Conversation::getThreads` folder-query builder, `SendNotificationToUsers` medium matrix internals, `CheckRequirements` installer probes). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
FreeScout (AGPL-3.0 — patterns only, never verbatim), `master@ab2772536811d5de6e23121c5d086aeb50f3db2c` (dist merge 2026-08-15, working tree clean at pin); Codebase Memory project `ext-freescout` (ready, root `/mnt/hdd/utopia/inspo/external/freescout`, 35,478 nodes / 73,198 edges, FULL mode, generation 2026-08-23T11:46Z generation_matches=true, indexed_at 2026-08-23T11:46:03Z recording complete; parse_partial ×77 = blade views/CSS/minified assets — none cited here; skipped 0; not_indexed = vendor/, Modules/, built assets, images BY DESIGN).

## Full view (memory graph)
Revalidate `ext-freescout` before porting: run `index_status`, `check_index_coverage` (20 cited paths returned `no_recorded_issue` + `metadata_match` at the pinned generation), `search_graph` (all cited seam symbols resolve line-exact under BM25 rank#1, e.g. `separateReply` → FetchEmails.php 1530-1670, `checkUrlIpAndHost` → Helper.php 2097-2187), `trace_path`, and `get_code_snippet`. Source and direct tests decide shipped claims: upstream ships 6 small unit suites (ReplySeparationTest, SsrfProtectionTest, MessageIdAssasinTest, MailVarsTest, WebklexTest fixtures, StripTagsTest) — the four relevant suites are pinned inside their capsules; every other Probe is a deterministic source grep verified at pin ab277253. BM25 note: Method/Class nodes carry tokens; Module-level queries need file-stem terms.

## Boundaries
Adopt the portable contracts: pagination predicates, hash-witnessed identity grammars, separation/counting ladders, retry-and-idempotence state machines, driver-swap hashing, deferred flush timing, SSRF candidate expansion, access ordering. Adapt Laravel/Eloquent plumbing (observers, policies, mailables, Eventy filters, Option table, cache locks) to your framework's equivalents while preserving each invariant's shape. Omit product surface: blade views/assets, install/update wizards, translation manager, module marketplace UI, Docker/nginx configs, and the proprietary modules absent from this OSS tree.
