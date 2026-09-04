<!-- capsule-v2 -->
# Hook↔permission arbitration ladder — how do PreToolUse decisions compose with settings rules?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a PreToolUse hook says allow/deny/ask/passthrough, how is that combined with rule-based permissions and interactive dialogs without letting either side bypass the other?

## resolveHookPermissionDecision + runPreToolUseHooks
**Path/Symbol:** `src/services/tools/toolHooks.ts` — `resolveHookPermissionDecision` (:332-433, shared with REPLTool wrappers), `runPreToolUseHooks` (:435-650), `runPostToolUseHooks` (:39-191), `runPostToolUseFailureHooks` (:193-319).
**Signature:** `resolveHookPermissionDecision(hookPermissionResult | undefined, tool, input, toolUseContext, canUseTool, assistantMessage, toolUseID) → { decision: PermissionDecision; input }`.
**Data Shape:** runPreToolUseHooks yields a tagged union: `{type:'message'|'hookPermissionResult'|'hookUpdatedInput'|'preventContinuation'|'stopReason'|'additionalContext'|'stop'}` — 'stop' is terminal (aborted mid-hooks or hook-execution crash).

### Decisive source
```ts
// :372-384 hook allow STILL passes the rule engine
// Hook allow skips the interactive prompt, but deny/ask rules still apply.
const ruleCheck = await checkRuleBasedPermissions(tool, hookInput, toolUseContext)
if (ruleCheck === null) {
  return { decision: hookPermissionResult, input: hookInput }   // rules silent → hook wins
}
if (ruleCheck.behavior === 'deny') {
  return { decision: ruleCheck, input: hookInput }              // deny rule overrides hook allow
}
// ask rule → dialog required despite hook approval (:392-405)
// :347-370 requiresUserInteraction / requireCanUseTool guards force canUseTool even on hook allow;
// updatedInput on an interactive tool SATISFIES the interaction (hook IS the user interaction)
const interactionSatisfied = requiresInteraction && hookPermissionResult.updatedInput !== undefined
```

**Flow:** executeHooks fans matched hooks out in PARALLEL with individual timeouts (combined signal + cleanup) → aggregate pass applies permission precedence deny > ask > allow across hook results and splits passthrough-updatedInput (input mutation WITHOUT a decision) from decided-updatedInput → toolExecution consumes: passthrough updates processedInput then flows through the normal ladder; allow enters resolveHookPermissionDecision (rules can still deny / force ask / demand canUseTool); deny short-circuits with the hook's message; ask forwards `forceDecision` so the dialog shows the hook's reason → crash inside hook iteration yields 'stop' (tool never runs).

**Invariant:** (1) NO single source wins absolutely: hook allow < deny-rule; hook deny beats everything (returned before rule check); ask-rule beats hook allow; requireCanUseTool (SDK headless) beats hook allow. (2) Passthrough updatedInput is a distinct channel from decided updatedInput — merging them lets input mutations bypass the permission audit trail. (3) PostToolUse blocking feedback is CONTINUE-with-feedback: blockingError becomes a synthetic denial tool_result fed back to the model, while preventContinuation ends the turn — two different "block" meanings that porters routinely conflate (#31301: JSON-block hooks yield both blockingError AND a hook_blocking_error message attachment; the runner suppresses the duplicate (:92-101, :245-253)). (4) PostToolUseFailure hooks fire with isInterrupt flagged so failure handlers can ignore user cancels.

**Probe:** coverage caveat — no upstream tests. Deterministic pins: `grep -n "deny/ask rules still apply" src/services/tools/toolHooks.ts` (:372); `grep -n "inc-4788 analog\|stay in lockstep" src/services/tools/toolHooks.ts` (:325-330); `grep -n "#31301" src/services/tools/toolHooks.ts` (:92, :245); graph resolves `src.services.tools.toolHooks.resolveHookPermissionDecision` line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "resolveHookPermissionDecision checkRuleBasedPermissions forceDecision", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the four-way arbitration matrix and the passthrough-vs-decided input split verbatim; adapt rule-engine entry points; omit REPL dual-site sharing if you have one call path. Porting trap: treating hook allow as unconditional bypass reintroduces the inc-4788 vulnerability class; treating PostToolUse blockingError as turn-ending breaks continue-with-feedback loops.
