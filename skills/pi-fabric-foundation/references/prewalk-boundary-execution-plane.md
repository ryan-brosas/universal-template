<!-- capsule-v2 -->
# Prewalk boundary execution plane — how do you run a delegated model switch/handoff at a tool-result boundary so Main never idles, stale continuations never fire, and failures degrade to results instead of throws?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** given an armed plan-first handoff FSM and a completed outer tool result, what is the exact execute-side choreography — claim precedence, in-place model switch, trajectory executor seed, continuation identity, settle-back, and re-arm directive?

## Claim → run → settle pipeline over the arm state machine
**Path/Symbol:** `src/prewalk/handoff.ts` whole file (543L): `prewalkContinuationId` (:48-61), `filterPrewalkContinuationMessages` (:63-76), `prewalkArmedPrompt` (:81-89), `hasPrewalkArmedPrompt` (:110-122), `withTrajectoryRearmDirective` (:149-160), `claimFabricHandoff` (:162-216), `runInPlacePrewalk` (:231-338), `settleInPlacePrewalk` (:361-428), `runFabricHandoffAtBoundary` (:431-543). Direct tests `tests/prewalk-handoff.test.ts` whole (1,131L, 32 cases) + `tests/prewalk-prompt.test.ts:72-99`.
**Signature:** `claimFabricHandoff(controller, execution, sessionId, resultFormat): PendingFabricHandoff | undefined`; `runFabricHandoffAtBoundary(controller, runner, extension, pending, outerToolResult, context, activity?): Promise<Record<string, unknown>>`; `settleInPlacePrewalk(controller, extension, context, options?): Promise<boolean>`; `PendingFabricHandoff = {kind: "explicit"|"prewalk-in-place"|"prewalk-trajectory", args, audit, resultFormat, triggerRef?}`.

### Decisive source
```ts
// Identity filtering applies to in-place continuations ONLY (:56-59): they carry
// the accept/settle lifecycle. The trajectory verify prompt shares customType
// pi-fabric-prewalk-continue but has NO continuation identity and must always
// reach Main.
const prewalkContinuationId = (message) => {
  if (custom.role !== "custom" || custom.customType !== PREWALK_CONTINUE_MESSAGE_TYPE) return undefined;
  if (details.mode !== "in-place") return undefined;   // ← trajectory bypasses the gate
  return typeof details.continuationId === "string" ? details.continuationId : "";
};
// claim precedence: explicit deferred request WINS over the armed task (:168-187)
if (execution.handoffRequest) {
  controller.completeTask();                            // disarm before claiming
  // audit MUST exist or the claim throws — no orphan handoffs
  for (let i = execution.audits.length - 1; i >= 0; i--)
    if (execution.audits[i]?.ref === "agents.handoff") { audit = execution.audits[i]; break; }
  if (!audit) throw new Error("Deferred agents.handoff request has no matching Fabric audit");
}
// settle: compact BEFORE restoring so the restored model re-ingests a compacted
// transcript (:383-398) — already-pending intent wins, commit is best-effort
if (!options.compact.status?.().pending)
  options.compact.request({ reason: "in-place prewalk return",
    instructions: PREWALK_RETURN_COMPACTION_INSTRUCTIONS, requestedBy: "prewalk" });
await options.compact.maybeCommit(context);             // then setModel back
```

**Flow:** fabric_exec execute() claims via `state.claimHandoff` → at the outer `message_end` boundary `runFabricHandoffAtBoundary`: (in-place) resolve target model from registry (`modelForKey` requires `provider/model`, throws otherwise) → snapshot source thinking channel → `extension.setModel(target)`; on failure throw `No authentication configured for prewalk model` → send optional bounded thinking digest (`deliverAs: "followUp"` ×3 sites, `triggerTurn: true` only on continuations) then the CONTINUE prompt carrying fresh `continuationId` + `returnModelKey` → `controller.beginContinuation(id, returnModel)`; on queue failure restore return model first, then rethrow (:313-322). (trajectory) `snapshotHandoffSession` clones branch+model+outer result into a session seed → `runner.executeHandoff(args, invocation, seed)` as a nested child agent → on `completed===true` best-effort hidden verify-and-summarize follow-up (swallowed on error — a missed verification turn must not fail the handoff :500-502). Error path returns `{handedOff:false, continued:false, completed:false, status:"failed", error}` — NEVER throws to the outer boundary (:514-534); `controller.failHandoff()` only for in-place; finally-block `completeTask()` re-arms for non-in-place kinds (:535-541). Settle consumes `takeContinuationSettlement(sessionId)`; unresolvable return model finishes the continuation and reports once without retrying (:372-380).
**Invariant:** every queued continuation carries an identity that `filterPrewalkContinuationMessages` enforces against `controller.acceptContinuation` — stale identities are silently dropped from context, trajectory prompts bypass the filter by construction (test :314 asserts the accept callback would THROW if reached); `withTrajectoryRearmDirective` appends only when kind=prewalk-trajectory AND handoff.completed===true AND controller.isArmed(sessionId) — one-shot arms stay silent (tests :1104/:1113/:1119/:1126); audits record success/result/error symmetrically for all three kinds; the index.ts consumer (:427-473) formats/truncates output FIRST and appends the directive AFTER truncation so it survives `maxOutputChars`, then sets `isError: !(handoff.completed || handoff.continued)`.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-ecosystem/pi-fabric && grep -c "deliverAs: \"followUp\"" src/prewalk/handoff.ts'` → 3; `grep -n 'reason: "in-place prewalk return"' src/prewalk/handoff.ts | wc -l` → 1 (:392); `grep -n 'mode !== "in-place"' src/prewalk/handoff.ts | wc -l` → 1 (:59); `grep -n 'requestedBy: "prewalk"' src/prewalk/handoff.ts | wc -l` → 1 (:394); tests pin behavior: `expect(compact.request).toHaveBeenCalledWith(expect.objectContaining({ reason: "in-place prewalk return", requestedBy: "prewalk" }))` :366-369, compaction ordered BETWEEN the two setModel calls via invocationCallOrder :370-376, `expect(claimFabricHandoff(...)).toMatchObject({kind:"explicit"})` :966-969, no-mutation ⇒ undefined + still armed :973-981.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "claimFabricHandoff settleInPlacePrewalk prewalk boundary handoff executor", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #1-3 resolve `claimFabricHandoff` :162-216, `settleInPlacePrewalk` :361-428, `runFabricHandoffAtBoundary` :431-543 line-exact at the pin.)

## Verdict
Adopt the claim-precedence ladder, continuation identity filtering with mode-bypass, compact-before-restore settle ordering, and result-not-throw boundary errors for any host that swaps models or delegates mid-session at a tool boundary; adapt the two prompt texts and the digest bounds to your vocabulary; omit the trajectory verify follow-up if your executors always self-verify. All branches direct-test-pinned across two suites — no coverage caveat.
