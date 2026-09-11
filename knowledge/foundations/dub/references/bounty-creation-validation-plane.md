<!-- capsule-v2 -->
# Bounty creation/validation plane — how do you admit a two-type incentive object whose timing fields mean different things per mode?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When one object can be either machine-awarded (performance) or human-submitted (submission) and either calendar-anchored (absolute) or per-partner-anchored (relative), what admission gates keep the stored shape honest — and what must a PATCH refuse once submissions exist?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/bounty/api/validate-bounty.ts:validateBounty` (:5-131) · `apps/web/lib/bounty/bounty-period.ts:resolveBountyTiming` (:28-88) + `BOUNTY_DURATION_DAYS` (:13-17) · `apps/web/lib/bounty/api/generate-performance-bounty-name.ts:generatePerformanceBountyName` (:6-33) · routes `app/(ee)/api/bounties/route.ts:POST` (:168-384) + `[bountyId]/route.ts:PATCH` (:59-406) / `DELETE` (:408-476) · schema `apps/web/lib/zod/schemas/bounties.ts:createBountySchema` / `updateBountySchema` (omits type+performanceScope, re-declares startMode optional to dodge the inherited default).
**Signature:** `validateBounty(partial: Partial<CreateBountyInput>) => void` (throws DubApiError bad_request ×13); `resolveBountyTiming({startPreset, endPreset, customStartsAt?, customEndsAt?}) => {startMode, startsAt, endsAt, endsAfterDays}`.
**Data Shape:** type ∈ {performance, submission}; startMode ∈ {absolute, relative}; performanceScope ∈ {new, lifetime}; duration presets {twoWeeks:14, oneMonth:30, sixMonths:180} days; startPreset ∈ today|twoWeeks|oneMonth|sixMonths|onPartnerJoin|custom; endPreset ∈ never|presets|custom.

### Decisive source
```ts
// MODE-DEPENDENT TIMING GATES (validate-bounty.ts :18-51) — the same field is legal/illegal per mode:
startMode = startMode ?? BountyStartMode.absolute;
if (startMode === BountyStartMode.relative) { if (startsAt != null) throw ... "`startsAt` is not supported when the `startMode` is `relative`." }
else { startsAt = startsAt || new Date(); }                       // absolute defaults to now
if (endsAt && endsAfterDays) throw ... "cannot have both";        // XOR
if (startMode === absolute && endsAfterDays) throw ... "only supported when relative";
if (endsAt && startsAt && endsAt < startsAt) throw ...;
// SCOPE×MODE INTERACTION (:104-110): lifetime stats need a fixed anchor:
if (startMode === relative && performanceScope === "lifetime") throw ... "`lifetime` performance scope is not supported when the `startMode` is `relative`.";
// PRESET MAPPER (bounty-period.ts :57-79) — ONE preset word, TWO storage shapes per mode:
case "onPartnerJoin": startMode = BountyStartMode.relative; break;
case "twoWeeks" | "oneMonth" | "sixMonths":
  if (startMode === absolute) endsAt = addDays(startsAt, BOUNTY_DURATION_DAYS[endPreset]);
  else endsAfterDays = BOUNTY_DURATION_DAYS[endPreset];          // relative stores DAYS, not a date
// ROUTE WRITE GATES (bounties/route.ts POST): type-conditional ZEROING of inapplicable fields:
submissionsOpenAt: type === "submission" ? submissionsOpenAt : null,
maxSubmissions: type === "submission" ? maxSubmissions ?? 1 : 1,   // default 1 even when omitted
performanceScope: type === "performance" ? performanceScope : null,
// social-metrics plan gate (:207-211): forbidden "Social metrics criteria require Advanced plan or above."
// workflow row created INSIDE the bounty tx with the pre-minted id (:246-262): bountyId = createId({prefix:"bnty_"}) FIRST
// PATCH REFUSALS ONCE SUBMISSIONS EXIST ([bountyId]/route.ts :205-249): condition ATTRIBUTE change blocked
// (message names both human labels from PERFORMANCE_BOUNTY_SCOPE_ATTRIBUTES); socialMetrics deepEqual change blocked
// DELETE REFUSAL (:428-433): _count.submissions > 0 ⇒ bad_request "Bounties with submissions cannot be deleted. You can archive them instead."
```
**Flow:** POST parses createBountySchema → validateBounty (13 throws: relative⇒startsAt-null, absolute-defaults-now, endsAt⊕endsAfterDays, endsAfterDays-relative-only, endsAt≥startsAt, submissionsOpenAt∈[startsAt,endsAt] requiring endsAt, performance-requires-rewardAmount, submission-needs-amount-or-description, performance-requires-scope, lifetime+relative-forbidden, frequency⇒maxSubmissions, frequency⇒end-bound) → performanceCondition validated against the awardBounty workflow type → plan gate for social metrics (canUseBountySocialMetrics) → group/tag admission (throwIfInvalid*) → name synthesis for performance bounties ("Earn $X after generating Y <attribute>", range-object values take .min) → startsAt nulled for relative → ONE $transaction mints bnty_ id, creates the workflow row (performance condition) then the bounty with type-conditional zeroing + relation createMany → post-commit waitUntil fan-out: audit log, bounty.created webhook, notify-partners QStash (notBefore startsAt, gated on sendNotificationEmails ∧ canSendEmailCampaigns ∧ non-relative), upsert-draft-submissions QStash (lifetime ∧ non-relative). PATCH merges absent fields onto the row, runs the SAME validateBounty over the merged view (with relative-mode coercion so mode switches don't fail against leftover absolute values), applies the endsAt clearing ladder (explicit endsAt wins; endsAfterDays set ⇒ clear endsAt; absolute→relative switch clears a fixed endsAt; relative+calendar endsAt is a SUPPORTED custom-end shape never cleared on unrelated PATCHes) and the mirror startsAt ladder (relative ⇒ null; relative→absolute without startsAt ⇒ now), refuses attribute/socialMetrics changes when submissions exist, updates bounty+workflow in one tx, then re-fires the draft-upsert job only when shouldUpsertDraftSubmissionsOnReopen fires (see draft-submission-upsert-cron).
**Invariant:** (1) The stored shape encodes the mode: relative rows carry startsAt=null + optional endsAfterDays; absolute rows carry startsAt (+optional endsAt) and NEVER endsAfterDays — validation enforces this at BOTH create and patch, so a mode switch cannot leave a hybrid row. (2) Type-conditional zeroing happens at the ROUTE (not the schema): inapplicable fields are explicitly nulled on write, so a stale client value can't leak into a performance bounty's submission columns or vice versa. (3) Immutability escalates with state: type and performanceScope are omitted from updateBountySchema entirely (creation-only), while condition-attribute and social-metrics changes become soft-refused (bad_request with a human-readable message) once ANY submission exists — the prize rules cannot move under a partner mid-flight. (4) Deletion is count-gated: any submission makes the bounty archive-only, preserving the audit trail of partner work. (5) The workflow row is created in the same transaction as the bounty with a pre-minted id — no window where a bounty exists without its awarding workflow.
**Probe:** No direct test for validateBounty/resolveBountyTiming/generatePerformanceBountyName (glob tests/**/*bounty* = only the draft-upsert suite). Deterministic probes executed at pin: `throw new DubApiError` census in validate-bounty.ts = exactly 13; `BOUNTY_DURATION_DAYS` = {twoWeeks:14, oneMonth:30, sixMonths:180} at bounty-period.ts :13-17; `case "onPartnerJoin"` at :57 with the dual-storage branch at :76/:78; `type === "submission" ?` zeroing ×3 + `maxSubmissions ?? 1` at bounties/route.ts :280-285; `createId({ prefix: "bnty_" })` at :248 INSIDE the $transaction opened at :246; PATCH refusals at [bountyId]/route.ts :221 (condition attribute) and :246 (social metrics); DELETE refusal message at :430; NEGATIVE probe: updateBountySchema omits exactly {type, performanceScope} (schemas/bounties.ts) and re-declares startMode `.optional()` with a comment explaining the inherited-default trap.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "validateBounty startMode relative endsAfterDays lifetime performance scope", limit: 10 }); // rank-1 expected: validate-bounty.ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "resolveBountyTiming startPreset endPreset duration presets", limit: 10 }); // rank-1 expected: bounty-period.ts
```

## Verdict
Adopt the mode-dependent validation ladder (field legality keyed off the mode enum, checked at both create and patch over the MERGED view) for any object whose columns mean different things per variant. Adopt route-level type-conditional zeroing plus creation-only schema omission for fields that must never migrate between variants. Adopt the state-escalating immutability ladder: creation-only ⇒ soft-refuse-with-message once dependents exist ⇒ hard delete refusal with the archive alternative. Adopt the pre-minted-id same-transaction companion-row pattern when an object's behavior depends on a second row (workflow, policy, config). Adapt the preset→storage mapper so one UI word maps to different column shapes per mode (days vs dates). Omit nothing silently: skipping the merge-view validation lets a PATCH smuggle a hybrid timing row; skipping the zeroing leaks cross-type column values into webhooks.
