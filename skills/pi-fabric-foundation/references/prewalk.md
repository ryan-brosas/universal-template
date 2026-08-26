<!-- capsule-v2 -->
# Prewalk — the plan-first handoff state machine

**Source:** pi-fabric (monotykamary) MIT `<branch>@<commit>`; Codebase Memory `pi-fabric`. **Question:** how does a "plan first, then hand off to implementation" mechanism arm on a mutation and settle back without losing the task?

## Connected graph-selected seam
**Path/Symbol:** `src/prewalk/controller.ts` (223 lines): `PrewalkController` (:48), `arm` (:56-82), `claim` (:196-217), `beginContinuation` (:104-116), `acceptContinuation` (:118-128), `takeContinuationSettlement` (:130-145), `finishContinuation` (:147-158), `settleTask` (:166-176), `completeTask` (:178-194), `failHandoff` (:160-164), `cancel` (:219-222); `PREWALK_TRIGGER_REFS = {pi.edit, pi.write, schema.commit}` (:5-9).
**Signature:** `arm({model, mode?, sessionId, task?, alwaysRearm?, thinking?})` — requires a `provider/model` executor target (`model.includes("/")`); `claim(audits, sessionId)` — fires when a successful trigger mutation (`pi.edit`/`pi.write`/`schema.commit`) is seen while armed.
**Data Shape:** `FabricPrewalkStatus = {state:"idle"} | {state:"armed"|"handing_off"} & FabricPrewalkArm | {state:"continuation_pending"} & FabricPrewalkContinuation`; `FabricPrewalkClaim {arm, mutation}`; task normalized to 20k chars.

### Decisive source
```ts
const PREWALK_TRIGGER_REFS = new Set(["pi.edit", "pi.write", "schema.commit"])
// arm requires a provider/model executor target
if (!model.includes("/")) throw new Error("Prewalk requires a provider/model executor target")
// claim fires on the first successful trigger mutation while armed
const mutation = audits.find((audit) => PREWALK_TRIGGER_REFS.has(audit.ref) && audit.success === true)
if (!mutation) return undefined
this.#status = { state: "handing_off", ...arm }
// completeTask: re-arm if alwaysRearm, else cancel
```

**Flow:** `arm` arms the prewalk with a target model + optional task (mode `in-place` default). `claim` watches the audit trail; on the first successful trigger mutation (`pi.edit`/`pi.write`/`schema.commit`), it transitions to `handing_off` and returns the arm + mutation. The handoff runs the plan model, then `beginContinuation` → `acceptContinuation` → `takeContinuationSettlement` (returns the continuation + return/executor models) → `finishContinuation`. `completeTask` re-arms if `alwaysRearm`, else cancels. `failHandoff` returns to `armed`; `settleTask` completes without a continuation.
**Invariant:** a claim only fires on a SUCCESSFUL trigger mutation while armed; a handoff never fires on `agents.handoff` (completes instead); the task is normalized (20k cap); re-arm is opt-in (`alwaysRearm`).
**Probe:** `tests/` prewalk coverage (arm requires provider/model; claim fires on pi.edit success, not on failure; begin→accept→settle→finish sequence; failHandoff returns to armed; alwaysRearm re-arms).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "PrewalkController arm claim handoff continuation mutation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prewalk state machine (arm → claim-on-mutation → handoff → continuation settle → re-arm/cancel); adapt the trigger refs and executor model to host.
