<!-- capsule-v2 -->
# Mode-reminder state machines — how do plan/auto mode reminders cycle full→sparse and reset on exit?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the attachment-borne FSM that keeps permission-mode guidance fresh without spamming.

## plan_mode / auto_mode collectors
**Path/Symbol:** `getPlanModeAttachments` (:1186-1242), `getPlanModeExitAttachment` (:1248-1273), `getAutoModeAttachments` (:1335-1374), `getAutoModeExitAttachment` (:1380-1400), configs (:259-267, :291-293).
**Signature:** `(messages?, toolUseContext) → Attachment[]`; one-shot exits driven by module-state flags (`needsPlanModeExitAttachment/setNeedsPlanModeExitAttachment`, `hasExitedPlanModeInSession/setHasExitedPlanMode`).
**Data Shape:** `plan_mode { reminderType: 'full'|'sparse', isSubAgent, planFilePath, planExists }`; cadence constants `TURNS_BETWEEN_ATTACHMENTS: 5`, `FULL_REMINDER_EVERY_N_ATTACHMENTS: 5`.

### Decisive source
```ts
// Check for re-entry: flag is set AND plan file exists
if (hasExitedPlanModeInSession() && existingPlan !== null) {
  attachments.push({ type: 'plan_mode_reentry', planFilePath })
  setHasExitedPlanMode(false) // Clear flag - one-time guidance
}
const attachmentCount = countPlanModeAttachmentsSinceLastExit(messages ?? []) + 1
const reminderType = attachmentCount % FULL_REMINDER_EVERY_N_ATTACHMENTS === 1
  ? 'full' : 'sparse'
```

**Flow:** gate on permission-context mode (auto variant ALSO fires under `mode === 'plan' && isAutoModeActive()` — plan-with-auto) → human-turn throttle from reminder-turn-throttle capsule → re-entry sentinel emitted once when flag ∧ plan-file-exists (re-entry guidance differs from first entry) → main reminder with full/sparse cadence counted since last EXIT attachment. Exit collector: fire only when flag set AND actually out of the mode (in-mode clears flag silently); emits ONE exit attachment then clears its own flag — every emission is a state transition, not a query.
**Invariant:** reminders are pure functions of transcript sentinels + module flags; counting MUST restart at exit attachments or re-entry inherits the stale full/sparse phase; exit notifications must clear their trigger flags unconditionally (checked-or-not) to avoid zombie repeats; auto's exit suppression covers BOTH `mode==='auto'` and plan-with-auto-active.
**Probe:** no upstream test (coverage caveat). Deterministic probe: `sed -n '1215,1230p' src/utils/attachments.ts` pins reentry+cadence; exit flag clearing at :1256-1263/:1387-1399.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "plan_mode attachments reminderType sparse reentry exit", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt sentinel-anchored full/sparse cycling with one-shot exit transitions; adapt modes/cadence; omit subscription/feature gates. Porting trap: continuing the modulo count across an exit makes the first post-re-entry reminder randomly sparse; forgetting to clear one-shot flags turns a single transition into a repeated announcement every turn.
