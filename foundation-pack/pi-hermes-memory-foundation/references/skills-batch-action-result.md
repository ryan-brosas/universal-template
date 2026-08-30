<!-- capsule-v2 -->
# Skills batch-action protocol — per-item try/catch turns store failures into data, and every UI state (selection, focus, summary) is derived from the result object

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** A user multi-selects 20 skills and hits "move to project" — how do you report partial success without losing the selection or leaving the modal in an unknown state?

## moveSelectedSkills / deleteSelectedSkills
**Path/Symbol:** `src/handlers/skills-command.ts` — `moveSelectedSkills` (:441–499), `deleteSelectedSkills` (:501–542), `confirmDeleteSelectedSkills` (:544–569), `summarizeAction` (:395–428), stores narrowed to `SkillMoveStore = Pick<SkillStore,"move"|"loadIndex"|"getProjectName">` / `SkillDeleteStore` (:430–431), result contract `SkillBatchActionResult` (:434–439).
**Signature:** `(store, skillIds: string[], targetScope?: SkillScope) → Promise<SkillBatchActionResult>` where the result is `{ skills: SkillIndex[] (refreshed index), summaryLines: string[], retainSelectedSkillIds?: string[], focusSkillId?: string }`.
**Data Shape:** three outcome buckets per batch — `successes: SkillResult[]`, `unchanged: SkillResult[]` (result already at target: `result.skillId === skillId && result.scope === targetScope`), `blocked: {skillId, error}[]`; thrown errors are caught PER ITEM and pushed into `blocked`.

### Decisive source
```ts
const focusSkillId = blocked[0]?.skillId ?? successes[0]?.skillId ?? unchanged[0]?.skillId;
return {
  skills: refreshedSkills,                       // ALWAYS a fresh loadIndex() after the loop
  summaryLines: summarizeAction("moved", targetScope, successes, unchanged, blocked),
  retainSelectedSkillIds: blocked.map((item) => item.skillId),   // failures stay selected
  focusSkillId,
};
```
Pre-flight gates return early WITHOUT touching the index: empty selection ⇒ `"Select one or more skills first."`; move-to-project with no active project ⇒ `"Move to project is unavailable…"` + retain ids (:456–462). `summarizeAction` caps the blocked listing at 4 with an `…and N more` line (:419–424). Cancel path of `confirmDeleteSelectedSkills` returns the FULL original id list as `retainSelectedSkillIds` and `skillIds[0]` as focus (:559–566).

**Flow:** dedupe ids → load index → gate → per-item loop isolating throws → re-load index → derive all four UI channels from the result. The modal's `setRows(result.skills, retainSelectedSkillIds, focusSkillId)` rebuilds rows preserving exactly the retained selection and moving the cursor to the focus skill (:702–722); `appendExternalReadOnlySummary` folds read-only E-row refusals into the same result afterwards (:787–807).
**Invariant:** the store NEVER throws past the loop boundary — a porter who lets one failed `store.move()` reject the whole batch loses the partial-success report AND the refresh; equally, one who forgets the trailing `loadIndex()` renders stale rows after moves that change skillIds (scope prefix). Selection retention is the failure channel: "still selected" means "not done".
**Probe:** `tests/handlers/skills-command.test.ts` — "keeps partial successes and retains blocked selection" (:180), "treats thrown move errors as blocked items" (:250) / thrown delete errors (:269), "blocks project moves without an active project" (:167), "confirms delete in-modal with y" (:431) + cancel keeps selection (:287).
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "moveSelectedSkills deleteSelectedSkills summarizeAction SkillBatchActionResult", limit: 5 })`

## Verdict
Adopt for any bulk-operation surface over fallible items. Adapt verb wording and bucket names; keep per-item catch, post-batch re-read, retain-on-failure, and focus-first-failure. Omit nothing.
