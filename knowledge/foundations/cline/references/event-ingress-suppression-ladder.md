<!-- capsule-v2 -->
# event-ingress-suppression-ladder — how does event ingress dedupe, debounce, and rate-limit WITHOUT ever dropping a racing event?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When automation events arrive from webhooks, how do you persist-first, classify every suppression reason, and still enqueue fresh when a debounce UPDATE loses a race?

## Persist-before-match replay detection; five-rung recursive filter resolution; debounce-pushout vs dedupe-window vs cooldown; race-guarded UPDATE with fall-through
**Path/Symbol:** `sdk/packages/core/src/cron/events/cron-event-ingress.ts` (`CronEventIngress.ingestEvent` :180-268; `normalizeEvent` :95-118; `resolveFilterValue` :113-144 region; `matchesExpected` :146-160; `materializeForSpec` :270-356).
**Signature:** `ingestEvent(event: AutomationEventEnvelope): CronEventIngressResult` — `{event, duplicate, matchedSpecs, queuedRuns, suppressions}`; never executes agents.
**Data Shape:** Suppression reasons are a closed union: `duplicate_event | filter_mismatch | dedupe_window | cooldown`. dedupeKey synthesizes to `${eventType}:${source}:${subject ?? eventId}` when absent.

### Decisive source
```ts
const inserted = this.store.insertEventLog(normalized, { receivedAtIso: receivedAt });
if (!inserted.created) { return { …, duplicate: true, matchedSpecs: [], queuedRuns: [],
	suppressions: [{ reason: "duplicate_event", … }] }; }        // replay = DB fact, not a Set
// …per spec: debounce UPDATE is race-guarded and FALLS THROUGH:
const updated = this.store.updateQueuedEventRunForDebounce({ runId: existing.runId,
	triggerEventId: event.eventId, scheduledFor });               // max(existing, receivedAt+debounce)
if (updated) return { run: updated, reason: "dedupe_window" };   // changes!==1 ⇒ claimed mid-flight
// …then dedupeWindow (same dedupeKey, recent) ⇒ suppress; then cooldown
// (ANY recent run for the SPEC, regardless of dedupeKey) ⇒ suppress; else enqueueRun.
```

**Flow:** normalize (trim ids, ISO-normalize occurredAt→receivedAt fallback, synthesize dedupeKey, records-or-undefined payload/attributes) ⇒ INSERT OR IGNORE event log ⇒ duplicate short-circuits with ZERO spec matching ⇒ per candidate spec: filter check (`attributes[key]` → `payload[key]` → dot-path over envelope → dot-path into attributes → dot-path into payload; expected arrays ANY-of, actual arrays SOME, records every-key recursive, leaves Object.is; empty filters match everything) ⇒ materializeForSpec ladder ⇒ status projection unmatched/queued/suppressed with `suppressedCount` EXCLUDING filter_mismatch (routing ≠ throttling) ⇒ failure marks the log row failed THEN rethrows.
**Invariant:** The event is durable BEFORE any matching; a duplicate eventId can never requeue. The debounce UPDATE (`WHERE run_id=? AND trigger_kind='event' AND status='queued'`, changes===1) is race-guarded: if the runner claimed the pending run between find and update, ingress does NOT drop the event — it falls through to window/cooldown and possibly a FRESH enqueue. Ingress only materializes `cron_runs` rows; the runner claim loop owns execution. Debounce pushes `scheduledFor` out (max) and replaces triggerEventId with the LATEST event.
**Probe:** `grep -cF 'reason: "duplicate_event",' sdk/packages/core/src/cron/events/cron-event-ingress.ts` → 1; `grep -cF 'if (updated) return { run: updated, reason: "dedupe_window" };' …` → 1; `grep -cF '`${eventType}:${source}:${subject ?? eventId}`' …` → 1. Direct suite `cron-event-ingress.test.ts` (8 cases, read whole) pins: dedupeKey byte-exact `"github.pull_request.opened:github:acme/api#12"`, unmatched status, one run per concurrently matching spec, replay no-requeue, dedupe-window suppression, debounce push-out (same runId, triggerEventId evt_2, scheduledFor 10:00:40 from 10:00:10+30s), cooldown across DIFFERENT dedupe keys (pr:13 suppressed during pr:12's cooldown).

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.cron.events.cron-event-ingress.CronEventIngress.ingestEvent" });
```

## Verdict
Adopt persist-first replay detection via an INSERT constraint, the three-distinct-semantics suppression ladder (debounce push-out / dedupe window / spec-wide cooldown), the race-guarded UPDATE with fall-through, and filter_mismatch excluded from throttling counts. Adapt reason names, the dedupeKey template, and filter resolution depth. Omit Cline's runner claim loop (separate plane). Coverage: source+test read whole at pin; MCP coverage check not runnable this session — recorded caveat.
