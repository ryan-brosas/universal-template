<!-- capsule-v2 -->
# Fraud detection entry gate ladder — which conditions silently skip fraud evaluation, and why does every skip return `[]` instead of throwing?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** Where does conversion-event fraud detection enter, what gates run BEFORE any rule fires, and what is the failure contract when a rule itself throws?

## Entry funnel with three silent skips and one loud catch
**Path/Symbol:** `apps/web/lib/api/fraud/detect-record-fraud-event.ts:detectAndRecordFraudEvent` (:10–97).
**Signature:** `async function detectAndRecordFraudEvent(context: FraudEventContext): Promise<Pick<CreateFraudEventInput, "type" | "metadata">[]>`.
**Data Shape:** input validated by `fraudEventContext` zod object (`apps/web/lib/zod/schemas/schemas.ts:4-34`: program.id, partner {id,email,name}, programEnrollment pick {status, riskMonitoringDisabledAt}, customer {id,email,name,isFirstConversion nullish}, link {id nullable optional}, click {url,referer,referer_url optional}, event.id). Output = array of triggered `{type, metadata}` rows (also the value passed to `createFraudEvents`).

### Decisive source
```ts
const result = fraudEventContext.safeParse(context);
if (!result.success) {
  console.error(`[detectAndRecordFraudEvent] Invalid context ${result.error}`);
  return [];                       // skip 1: malformed context never throws
}
if (INACTIVE_ENROLLMENT_STATUSES.includes(programEnrollment.status)) return [];   // skip 2: banned/deactivated/rejected
if (programEnrollment.riskMonitoringDisabledAt) return [];                        // skip 3: partner opted out
...
for (const rule of activeRules) {
  try {
    const { triggered, metadata } = await executeFraudRule({ type: rule.type, config: rule.config, context: validatedContext });
    if (triggered) triggeredRules.push({ type: rule.type, metadata });
  } catch (error) { console.error(...) }   // one broken rule NEVER kills the other rules
}
if (triggeredRules.length === 0) return [];
await createFraudEvents(triggeredRules.map(...));   // persistence is a separate concern
return triggeredRules;
```
(detect-record-fraud-event.ts :11-29, :53-77 condensed)

**Flow:** safeParse → inactive-status gate (`INACTIVE_ENROLLMENT_STATUSES` = banned/deactivated/rejected, `lib/zod/schemas/partners.ts:43-47`) → riskMonitoringDisabledAt gate → load program's FraudRule rows (:40-44) → merge with global defaults via `getMergedFraudRules` → filter `.enabled` → evaluate each rule serially with per-rule try/catch → persist triggered set through `createFraudEvents` → return triggered list to caller.
**Invariant:** (1) detection is BEST-EFFORT by design — a context-shape change, disabled enrollment, or one exploding rule must never block commission creation upstream; (2) rules are evaluated SERIALLY in merged order, and each rule sees the same immutable `validatedContext`; (3) `createFraudEvents` runs only when ≥1 rule triggered — an empty triggered set performs zero DB writes; (4) the return value doubles as the caller's `riskRulesTriggered` boolean source (`triggeredRules.length > 0`).
**Probe:** anchored at dub repo root: `grep -c 'return \[\];' apps/web/lib/api/fraud/detect-record-fraud-event.ts` = **4** (three skips + empty-triggered early return); `grep -c 'catch (error)' apps/web/lib/api/fraud/detect-record-fraud-event.ts` = **1** (single per-rule catch); `grep -rc 'detectAndRecordFraudEvent(' apps/web/app --include='*.ts' | grep -v ':0'` = exactly **1** route call site (`app/(ee)/api/workflows/create-partner-commission/route.ts`). Direct tests: E2E integration suites `apps/web/tests/fraud/index.test.ts` (six rule-trigger flows through `/track/click`→`/track/lead`→poll `/fraud/events`) exercise this funnel end-to-end via HTTP only.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "detectAndRecordFraudEvent", limit: 5 });
```

## Verdict
Adopt the silent-skip posture (fraud monitoring degrades gracefully, never blocks revenue events) and the per-rule isolation catch. Adapt the enrollment-status enum values and the context schema fields to host. Omit the console logging dialect. Coverage caveat: no unit suite isolates this function — behavior is pinned by the six E2E integration flows plus these deterministic greps.
