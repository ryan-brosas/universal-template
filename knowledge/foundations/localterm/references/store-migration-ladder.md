<!-- capsule-v2 -->
# Automation store migration ladder — how do versioned strict-schema files migrate AND repair without stranding user data?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I evolve a persisted automation file across 4 schema versions — including repairs for data written by OLDER builds that the CURRENT schema now rejects?

## v4 fast path → in-place repair → v3/v2/v1 migrations → empty
**Path/Symbol:** `packages/server/src/automation-store.ts:AutomationStore.load` (429–492), `repairAutomationsJson` (107–154), `migrateV1/V2/V3Automation` (40–99), `trimRunsToCap` (496–505), atomic `persist` (507–513).
**Signature:** `load(): void` (constructor-time, sync); private `repairAutomationsJson(json: unknown): boolean`; `persist(): void`.
**Data Shape:** file `{version: 4, automations: [...]}`; run history ring capped at AUTOMATION_RUN_HISTORY_CAP = 20 newest-first; per-field caps MAX_AUTOMATION_LOG_LENGTH / TOOL_RESULT / FINDINGS.

### Decisive source
```ts
// :446-463 — repair BEFORE declaring the file invalid
const v4 = automationsFileSchema.safeParse(json);
if (v4.success) {
  this.automations = v4.data.automations;
  if (this.trimRunsToCap()) this.persist();
  return;
}
// Repair: an older build stored a log/findings text above the current
// per-field cap (truncated to cap + marker), so the v4 schema rejected the
// file and the user's automations vanished. Truncate in place + revalidate.
if (repairAutomationsJson(json)) {
  const v4Repaired = automationsFileSchema.safeParse(json);
  if (v4Repaired.success) { ...; return; }
}
```

**Flow:** try current schema → try REPAIR (strip removed `autoCompact` runner flag; truncate over-cap findings/log/tool-result/thinking strings IN PLACE) → revalidate → else try v3, v2, then v1 migrations oldest-last; every successful path persists immediately so later loads hit the fast path; total failure warns and starts EMPTY (never throws). Migration semantics carry the traps: v1's single `lastRun` folds into a one-entry history where `finishedAt` is set ONLY for terminal statuses (`completed|failed|missed`) and `countsTowardLimit = status !== "missed"`; `runCount` seeds at 0 so a migrated automation can never be spuriously "finished"; v1's raw cron string goes through `normalizeScheduleInput` (recognize-preset or stay raw). Lifecycle rules live in the mutations themselves: `"finished"` is sticky under PATCH (only `reset()` un-finishes), but a PATCH that lowers `limit.max` below `runCount` finishes IMMEDIATELY (:218-219); only scheduled launches call `incrementRunCount`, so manual runs never consume budget. Webhook ids are finalized AFTER normalization: PATCH-preserving webhook kind keeps the existing id (editing a command never rotates the CI-configured URL), creates keep the proposed id unless it collides (:413–427).
**Invariant:** migrations are one-way and persist-once; repair mutates only fields the current schema rejects, never reorders or drops automations; corrupt JSON ⇒ empty list with a warning, never a crash loop.
**Probe:** `packages/server/tests/automation-store.test.ts` — `"repairs a v4 file with a stored log text above the per-entry cap instead of rejecting it"` (:76), `"strips the removed autoCompact flag from an agent runner on load"` (:110), `"migrates a missed v1 lastRun without counting it toward a limit"` (:434), `"finishes immediately when a PATCH lowers the limit below the run count"` (:304), `"never un-finishes through a normal update"` (:313), `"loads a v4 file whose run history exceeds the trim cap..."` (:51).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "AutomationStore repairAutomationsJson finalizeTrigger migrateV1Automation", limit: 8, detail: "compact" });
// → finalizeTrigger @ automation-store.ts:413-427, repairAutomationsJson @ :107-154, migrateV1Automation @ :40-76
```

## Verdict
Adopt the ordered ladder (validate → repair → migrate-old-to-new) and the sticky-lifecycle/limit-lowering rules verbatim; adapt field caps, version constants, and webhook-id policy to host storage; omit the v1/v2 legs if your port starts at the current shape. 34 direct tests pin the store at this commit.
