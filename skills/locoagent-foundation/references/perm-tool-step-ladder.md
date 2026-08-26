<!-- capsule-v2 -->
# Tool-permission step ladder — numbered gates, bypass-subset export, mode transforms at the tail

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** In what ORDER must deny rules, ask rules, tool self-checks, safety checks, bypass modes, and always-allow rules evaluate so no rule can be bypassed — and how do you expose the rule-only subset to killswitches?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/permissions.ts` — `PERMISSION_RULE_SOURCES` (:109-114), `toolMatchesRule` MCP server/wildcard match (:238-269), `hasPermissionsToUseToolInner` step ladder (:1158-1319), `checkRuleBasedPermissions` bypass subset (:1071-1156), dontAsk/auto transforms (:503-953), `runPermissionRequestHooksForHeadlessAgent` (:400-471), `getDenyRuleForAgent`/`filterDeniedAgents` Set-batch (:308-343).
**Signature:** `hasPermissionsToUseTool: CanUseToolFn (tool, input, context, assistantMessage, toolUseID) → PermissionDecision`.
**Data Shape:** Rules flatten from EIGHT sources (`SETTING_SOURCES + cliArg + command + session`) via parse-at-read; decisions are `{behavior:'allow'|'deny'|'ask', decisionReason, message?, updatedInput?, suggestions?}`; tool-check default is `passthrough`.

### Decisive source
```ts
// 1g. Safety checks (e.g. .git/, .claude/, .vscode/, shell configs) are
// bypass-immune — they must prompt even in bypassPermissions mode.
if (
  toolPermissionResult?.behavior === 'ask' &&
  toolPermissionResult.decisionReason?.type === 'safetyCheck'
) {
  return toolPermissionResult
}
```

**Flow:** 1a tool-wide deny → 1b tool-wide ask (Bash sandbox-auto-allow fall-through exception) → 1c `tool.checkPermissions` with schema-parsed input, abort errors rethrown, other errors logged → 1d tool deny → 1e `requiresUserInteraction()` ask survives bypass → 1f content-specific ASK rules survive bypass → 1g `safetyCheck` results are BYPASS-IMMUNE → 2a bypassPermissions (or plan-with-bypass-available) allow → 2b tool-wide allow → 3 passthrough→ask conversion. THEN the outer wrapper applies mode transforms that early returns cannot skip: dontAsk converts ask→deny; auto mode runs the classifier ladder (acceptEdits-probe fast path excluding Agent/REPL, safe-tool allowlist, then classifyYoloAction with iron-gate fail-closed/fail-open and denial-limit fallback); headless (`shouldAvoidPermissionPrompts`) routes through PermissionRequest hooks before auto-deny. `checkRuleBasedPermissions` re-executes ONLY 1a-1g for the bypass killswitch — documented as "the subset bypassPermissions respects".

**Invariant:** (1) The numbering IS the contract — steps 1d/1e/1f/1g exist precisely so deny rules, interactive tools, content-specific asks, and safety checks all outrank bypassPermissions; a porter who collapses them into one "rules first" phase silently grants bypass over safety checks. (2) Mode transforms live in the OUTER wrapper, after Inner returns, so no Inner path can bypass them ("done at the end so it can't be bypassed by early returns", :504). (3) Non-abort exceptions from tool checkPermissions become log-and-continue, NOT deny — availability failures degrade to later gates. (4) MCP matching: rule `mcp__server` or `mcp__server__*` matches every tool on the server; in SDK skip-prefix mode, builtin-name rules must NOT match unprefixed MCP replacements (`getToolNameForPermissionCheck`). (5) Agent-deny filtering parses once into a Set (O(agents+rules)), not per-agent re-parse.

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF 'are' -e 'bypass-immune' src/utils/permissions/permissions.ts | head -2` → :1145 & :1252; `grep -cF '1f. Content-specific ask rules' src/utils/permissions/permissions.ts` → 2 (duplicated deliberately in both ladders); `grep -nF 'const shouldBypassPermissions =' src/utils/permissions/permissions.ts` → :1268; graph search `syncPermissionRulesFromDisk` → permissions.ts :1419-1471 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "hasPermissionsToUseToolInner checkRuleBasedPermissions toolMatchesRule", limit: 8 });
```

## Verdict
Adopt the numbered gate order with its explicit bypass-immune steps, the tail-positioned mode transforms, and the exported rule-only subset for killswitches. Adapt source list and analytics plumbing. Omit the auto-mode classifier internals here (see perm-yolo-two-stage-classifier.md) and ant-only telemetry fields.
