<!-- capsule-v2 -->
# Session runner drain loop — how do you drain a durable input ledger into provider turns with steering vs queued delivery semantics, max-step enforcement, and single-shot compaction recovery?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** The v2 engine records prompts into a durable input ledger (pass-8 capsule). What does the CONSUMER do: how does one drain turn promote steers vs queued rows, repair tool parts left open by a previous interruption, enforce an agent step cap at the protocol level, and rebuild the request after compaction without unbounded overflow retries?

## Drain eligibility + two-loop promotion
**Path/Symbol:** `packages/core/src/session/runner/llm.ts` (`run` :390-414, `runTurnAttempt` :173-360, promotion block :187-196, `failInterruptedTools` :119-133, `isUserDeclined` :145-149).
**Signature:** `run({sessionID, force}) → Effect<void, RunError>`; RunError = LLMError | Model.Error | MessageDecodeError | ContextSnapshotDecodeError | SystemContext.InitializationBlocked | ToolOutputStore.Error.
**Data Shape:** promotion = "steer" | "queue" | undefined; step counter starts at 1 and resets to 1 on any promotion; cutoff = EventV2.latestSequence(sessionID) at promotion time.

### Decisive source
```ts
// llm.ts:392-413 — the two-loop drain
const hasSteer = yield* SessionInput.hasPending(db, input.sessionID, "steer")
const hasQueue = hasSteer ? false : yield* SessionInput.hasPending(db, input.sessionID, "queue")
if (!input.force && !hasSteer && !hasQueue) return
yield* failInterruptedTools(input.sessionID)
let promotion: SessionInput.Delivery | undefined = hasSteer ? "steer" : hasQueue ? "queue" : undefined
let shouldRun = input.force || hasSteer || hasQueue
while (shouldRun) {
  let needsContinuation = true
  let step = 1
  while (needsContinuation) {
    const result = yield* runTurn(input.sessionID, promotion, step)
    needsContinuation = result.needsContinuation
    step = result.step + 1
    promotion = "steer"
    if (!needsContinuation) needsContinuation = yield* SessionInput.hasPending(db, input.sessionID, "steer")
  }
  shouldRun = yield* SessionInput.hasPending(db, input.sessionID, "queue")
  promotion = shouldRun ? "queue" : undefined
}
// llm.ts:187-196 — promotion asymmetry inside a turn
if (promotion) {
  const cutoff = yield* EventV2.latestSequence(db, session.id)
  let promoted = 0
  if (promotion === "steer") promoted = yield* SessionInput.promoteSteers(db, events, session.id, cutoff)
  if (promotion === "queue") {
    promoted += Number(yield* SessionInput.promoteNextQueued(db, events, session.id))
    promoted += yield* SessionInput.promoteSteers(db, events, session.id, cutoff)
  }
  if (promoted > 0) currentStep = 1
}
```

**Flow:** Eligibility: steer-pending OR queue-pending unless force (force = explicit resume performs one provider attempt even when no work is eligible). First action is durable repair: failInterruptedTools publishes Tool.Failed ("Tool execution interrupted") for every pending/running tool part left open by a previous interruption. Outer loop = queued deliveries (one row per outer iteration, FIFO); inner loop = continuation turns (tool-driven continuation plus mid-turn steers). Each turn: location check (session moved away from this node → interrupt), promotion block (steer → promote ALL rows below the latest-sequence cutoff; queue → promote ONE oldest queue row THEN all steers; any promotion resets the step budget to 1), system-context epoch initialize/prepare (baseline seq gates history loading), model resolve, history load, request build, compactIfNeeded (→ defect transition), snapshot capture, stream. After the stream settles: needsContinuation = local tool calls were made AND no provider error; then re-check steer-pending for same-turn continuation before falling back to the queue check.

**Invariant:** Queue rows promote strictly one-at-a-time in FIFO order; steers below the cutoff promote together; a promotion resets the step budget; interrupted tool parts are durably failed before any new work; a declined user prompt (PermissionV2.DeclinedError / QuestionV2.RejectedError die reasons in the settlement cause) halts the loop via interrupt instead of becoming model-facing output.
**Probe:** `packages/core/test/session-runner.test.ts`: "promotes queued inputs one at a time in FIFO order" (:2051), "promotes steers before the next queued input" (:2128), "coalesces multiple active steering prompts into one continuation turn" (:2193), "preserves durable queued input for a later wake after interruption" (:1965, pins hasPending("queue")===true after interruption), "starts a real runner turn after default prompt recording" (:614, pins exactly one request + projected user message). Source pin:
```bash
grep -n 'hasPending' packages/core/src/session/runner/llm.ts        # expect 4
grep -n 'failInterruptedTools' packages/core/src/session/runner/llm.ts  # expect 2
grep -n 'promoteSteers' packages/core/src/session/runner/llm.ts     # expect 2
```

## Max-steps freeze + defect-as-control-flow compaction
**Path/Symbol:** `packages/core/src/session/runner/llm.ts` (max-steps :202-221, TurnTransitionError :158-166, overflow recovery gate :288-296, recursive wrappers :362-388, eager tool settlement :258-278, decline gate :303-309).
**Signature:** `runTurnAttempt(sessionID, promotion, step, recoverOverflow?) → Effect<{needsContinuation, step}, RunError>` (scoped); wrappers `runTurn` / `runAfterOverflowCompaction`.
**Data Shape:** agent.info.steps optional cap; MAX_STEPS_PROMPT assistant message appended on the last step; toolChoice "none".

### Decisive source
```ts
// llm.ts:202-221 — the last step freezes tools at the protocol level
const isLastStep = agent.info?.steps !== undefined && currentStep >= agent.info.steps
const toolMaterialization = isLastStep ? undefined : yield* tools.materialize(agent.info?.permissions)
...
messages: [...toLLMMessages(context, model), ...(isLastStep ? [Message.assistant(MAX_STEPS_PROMPT)] : [])],
tools: toolMaterialization?.definitions ?? [],
toolChoice: isLastStep ? "none" : undefined,
// llm.ts:158-166 — compaction continuation is a DEFECT, not a return value
class TurnTransitionError extends Error { constructor(readonly transition: TurnTransition) { super() } }
const continueAfterCompaction = (step) => new TurnTransitionError({ _tag: "ContinueAfterCompaction", step })
// llm.ts:376-388 — the recursive wrapper catches the defect and rebuilds
const runTurn: RunTurn = Effect.fnUntraced(function* (sessionID, promotion, step) {
  return yield* runTurnAttempt(sessionID, promotion, step, compaction.compactAfterOverflow).pipe(
    Effect.catchDefect((defect) => {
      if (!(defect instanceof TurnTransitionError)) return yield* Effect.die(defect)
      yield* Effect.yieldNow
      if (defect.transition._tag === "ContinueAfterOverflowCompaction")
        return yield* runAfterOverflowCompaction(sessionID, undefined, defect.transition.step)
      return yield* runTurn(sessionID, undefined, defect.transition.step)
    }),
  )
})
// llm.ts:362-374 — overflow recovery is allowed exactly ONCE
if (defect.transition._tag === "ContinueAfterOverflowCompaction")
  return yield* Effect.die("Post-compaction provider attempt cannot recover another overflow")
```

**Flow:** When currentStep reaches the agent's step cap, tool materialization is skipped entirely, an assistant MAX_STEPS_PROMPT message is appended, and toolChoice "none" is sent — the model is told to wrap up and CANNOT call tools; a late tool-call event on the frozen step fails unsettled tools with "Tools are disabled after the maximum agent steps". Pre-request compactIfNeeded dies with ContinueAfterCompaction; the recursive runTurn wrapper catches the defect (yieldNow first — stack hygiene again) and re-runs the turn with promotion=undefined from compacted history. A context-overflow failure before any assistant output triggers compactAfterOverflow recovery exactly once via runAfterOverflowCompaction, which dies on a second overflow. Provider events publish under Semaphore(1) so publication order equals arrival order; local tool calls settle EAGERLY in a FiberSet while streaming continues, all settlements awaited before continuation; user-decline die reasons convert the settlement failure into a loop-halting interrupt; other interrupt paths fail unsettled tools ("Tool execution interrupted") and the active assistant ("Provider turn interrupted").

**Invariant:** The step cap is enforced at the protocol level (tool surface removed + toolChoice none), not by trusting the model; compaction continuation flows through typed defects caught at a fixed wrapper (unknown defects still die); overflow recovery is single-shot; publication order equals arrival order; a user decline halts the loop and never reaches the model as tool output.
**Probe:** session-runner.test.ts: "forces one compaction and retries after provider context overflow" (:1212), "persists a second context overflow after one recovery" (:1241), "recovers once from a raw context overflow failure" (:1264), "interrupts a source Location runner after a Session moves" (:690), "starts recorded local tools eagerly and awaits settlement before continuing" (:1687). Source pin:
```bash
grep -n 'toolChoice: isLastStep ? "none" : undefined' packages/core/src/session/runner/llm.ts  # expect 1
grep -n 'Post-compaction provider attempt cannot recover another overflow' packages/core/src/session/runner/llm.ts  # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionRunner run runTurnAttempt promoteSteers promoteNextQueued TurnTransitionError failInterruptedTools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-loop drain shape (outer = queued FIFO one-at-a-time, inner = continuation + mid-turn steers) for any durable input ledger with two delivery classes; adopt durable pre-run repair of interrupted in-flight work (fail open tool parts before new work); adopt protocol-level step-cap enforcement (remove the tool surface + toolChoice none) over prompt-level begging; adopt defect-as-control-flow for turn-level rebuilds (compaction) with a fixed catch wrapper and single-shot overflow recovery; adopt eager parallel tool settlement with ordered publication under a semaphore. Adapt the Location-mismatch interrupt to your own placement model; omit the x-session-affinity / promptCacheKey provider headers (provider-specific). Direct tests read (session-runner.test.ts sections :614-658, :1212-1330, :1687-1748, :1918-2230); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
