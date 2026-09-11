<!-- capsule-v2 -->
# ACP permission plane — when the sandbox agent asks "may I?", who answers, and which requests must fail closed?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** how does a bridge answer protocol permission requests from host state — and how do you apply a desired permission mode against capabilities the agent merely ADVERTISES?

## Request gate ladder (`createACPPermissionController`)
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/permission-controller.ts:requestPermission` (:38–118) + `shouldAutoApprove` (:128–148).
**Signature:** `({ turn, sessionId, permissionMode, hasPermissionModeMapping, emitToolCall, claimHostToolPermission }) => { requestPermission(request): Promise<Response>, cancelAll() }`.
**Data Shape:** module-counter ids `acp-permission-${++permissionRequestCounter}` (:88); pending map of cancellers; answers are `{outcome:{outcome:'selected', optionId}}` or `{outcome:{outcome:'cancelled'}}` — the controller never invents options.

### Decisive source
```ts
// :47–64 — missing one-time options cancel WITH a warning naming the gap
if (allowOnce == null || rejectOnce == null) {
  const missing = [ ...(allowOnce == null ? ['allow_once'] : []),
                    ...(rejectOnce == null ? ['reject_once'] : []) ];
  turn.emitWarning({ message: `... did not advertise ${missing.join(' and ')}.` });
  return cancelled();
}
// :128–148 — auto-approval truth table for UNMAPPED implementations only
if (permissionMode === 'allow-all') return true;
if (kind === 'read' || kind === 'search' || kind === 'think' || kind === 'fetch') return true;
return (permissionMode === 'allow-edits' &&
        (kind === 'edit' || kind === 'delete' || kind === 'move'));
```

**Flow:** wrong sessionId ⇒ warning + cancelled → missing `allow_once`/`reject_once` ⇒ warning naming the gap + cancelled (`allow_always` is deliberately unusable) → claimed host-tool call ⇒ auto-select `allow_once` with NO native approval and NO consumer emission — the call already crossed the host's own runPrompt approval machinery (:65–72) → unmapped implementation + `shouldAutoApprove` ⇒ auto-allow (read/search/think/fetch ALWAYS safe; edit/delete/move need `allow-edits`; `allow-all` covers the rest) → otherwise: mint approval id, `emitToolCall` BEFORE emitting `tool-approval-request` so consumers see what they're approving (:96–102), race host approval against cancellation in a `finally`-cleaned pending map (:104–117). `cancelAll()` cancels every pending request.

**Invariant:** a MAPPED mode disables the auto-approve shortcut entirely — the host decides even for read-only kinds (test :280–306), because an explicit mapping means the operator opted into per-request governance. Emission order is load-bearing: tool-call part first, approval event second (test pins `order == ['tool-call:call-1', 'approval:<id>]`, :112).

**Probe:** `packages/harness-acp/src/v1/bridge/permission-controller.test.ts` — `:129–154` host-tool claim bypasses native approval (zero events); `:165–188` each missing option fails closed with its name in the warning; `:214–248` nine-row auto-approve truth table; `:190–212` cancelAll resolves every waiter cancelled.

## Mode application validates EVERYTHING before touching anything (`configureACPPermissionMode`)
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/permission-mode.ts:configureACPPermissionMode` (:20–72).
**Data Shape:** mapping = three optional targets (`allow-reads`/`allow-edits`/`allow-all`), each `{type:'session-mode', modeId}` or `{type:'session-config-option', configId, value}`; throws `HarnessBridgeCapabilityUnsupportedError`.

**Flow:** requested target missing ⇒ unsupported error whose `'allow-all'` hint appears ONLY when that mapping exists (:35–45; hint asymmetry pinned by tests :60–81 vs :83–112) → then EVERY mapped sibling target is validated against the session's advertised capabilities BEFORE any request fires — an obsolete sibling mode aborts the requested one (:47–57; tests :254–296 assert `agent.request` never called) → application rides `session/set_mode` or `session/set_config_option`, where boolean configs get the explicit `type:'boolean'` discriminator (:70; test :243–251) and select values are validated against grouped option lists (:133–146).

**Probe:** `packages/harness-acp/src/v1/bridge/permission-mode.test.ts` — `:140–202` grouped select values; `:204–252` boolean discriminator on the wire; `:254–296` obsolete-sibling abort before ANY apply.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "permission request controller mode configure allow_once reject auto approve session capabilities", limit: 10 });
```
Live @pin: rank#1 `shouldAutoApprove :128-148`; `trace_path(configureACPPermissionMode)` callers_total=2 (ensureSession at start + runTurn).

## Verdict
Adopt: the four-rung gate ladder with named-gap warnings, host-tool auto-release, unmapped-mode truth table, mapped-mode-forces-host-decision, emit-before-ask ordering, validate-all-then-apply capability negotiation, and the conditional allow-all hint. Adapt kind vocabularies and mode names to your harness. Omit ACP's specific method objects. Coverage caveat: runner block stands (no node_modules → vitest unrunnable); anchors verified by direct reads at pin.
