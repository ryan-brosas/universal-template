<!-- capsule-v2 -->
**Source:** dub `removeGroupIdFromMoveRules` @ pin `29df217a29`
**Question:** When a group dies, how do other groups' auto-move rules that reference it stay valid?
**Path/Symbol:** `apps/web/lib/api/groups/remove-group-id-from-move-rules.ts` — `removeGroupIdFromMoveRules({programId, groupId})`; helper `scrubGroupIdFromConditions`
**Signature:** scans partnerGroups `id != groupId AND workflowId != null` with their workflow.triggerConditions; per-group safeParse, skip on parse failure (never throws on legacy payloads).
**Data Shape:** WorkflowCondition value for partnerGroup is string (eq) | string[] (in); scrub returns a NEW condition array.
**Decisive source:** :48-50 change detection by JSON.stringify equality — unchanged conditions skip the update entirely. Scrub rules :70-96: non-partnerGroup attributes pass through; eq matching the dead id → DROP the whole condition; in-array → filter the id, drop the CONDITION if the array empties (:84-86 — an empty in[] would match nothing and permanently disable the rule), keep original object when nothing removed (:88-90), else emit `{...condition, value: nextValue}`.
**Flow/Invariant:** Runs inside waitUntil AFTER the group tx commits (group-delete route) so scrubbed rules reference only live groups; combined with upsert-time conflict rejection this keeps the at-most-one-matcher invariant true across deletions.
**Probe (direct test):** from repo root: `grep -n 'JSON.stringify(nextConditions) === JSON.stringify(parsed.data)' apps/web/lib/api/groups/remove-group-id-from-move-rules.ts | cut -d: -f1` → `48`; `grep -c 'return \[\];' apps/web/lib/api/groups/remove-group-id-from-move-rules.ts` → `2`; direct behavior exercised via E2E group deletion flows (no dedicated unit spec — recorded caveat).
**Retrieve:** `echo '{"project":"mnt-hdd-utopia-inspo-platforms-dub","query":"removeGroupIdFromMoveRules scrub","limit":5}' | codebase-memory-mcp cli search_graph`
**Verdict:** adopt — empty-in-drops-condition semantics prevent silently dead rules after deletions.
