<!-- capsule-v2 -->
# Read-only verdict consumer — one boolean feeding both the permission bypass and concurrency scheduling, plus per-tool allowlist assembly

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Where does the read-only verdict plug into tool execution, and how does one file assemble platform- and user-dependent allowlists without duplicating tables?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/BashTool.tsx` — `isReadOnly` (:437-441) calling `checkReadOnlyConstraints(input, commandHasAnyCd(input.command))`, `isConcurrencySafe` (:434-436) delegating to `this.isReadOnly?.(input) ?? false`; `src/tools/BashTool/readOnlyValidation.ts` `getCommandAllowlist` (:1201-1215) with Windows xargs-drop and `process.env.USER_TYPE === 'ant'` merge of ANT_ONLY_COMMAND_ALLOWLIST (:1141-1199, incl. aki); PowerShell twin `src/tools/PowerShellTool/readOnlyValidation.ts` importing GIT/GH maps + validateFlags (:22-29, calls at :1700/:1726) and mirroring checkReadOnlyConstraints (:1106).
**Signature:** `getCommandAllowlist(): Record<string, CommandConfig>`; `isConcurrencySafe(input): boolean`.
**Data Shape:** allowlist = COMMAND_ALLOWLIST ∪ (ant? ANT_ONLY) − (windows? xargs); verdict flows as PermissionResult.behavior.

### Decisive source
```ts
isConcurrencySafe(input) {
  return this.isReadOnly?.(input) ?? false;
},
isReadOnly(input) {
  const compoundCommandHasCd = commandHasAnyCd(input.command);
  const result = checkReadOnlyConstraints(input, compoundCommandHasCd);
  return result.behavior === 'allow';
},
```

**Flow:** BashTool declares isReadOnly by composing the compound-cd pre-computation with checkReadOnlyConstraints → 'allow' ⇒ the command skips permission prompts AND is marked safe to run CONCURRENTLY with other tools → anything else ('passthrough'/'ask') falls through to the rule engine/user dialog. Allowlist assembly happens per call: platform gate removes xargs on Windows; USER_TYPE gate appends ant-only network commands. The PowerShell tool reuses the SAME shared maps through import rather than copying them.

**Invariant:** (1) One verdict, two consumers: correctness here gates BOTH security (no unintended auto-approval) AND scheduling (no unsafe parallelism) — a false 'allow' doubles its blast radius. (2) compoundCommandHasCd is computed ONCE by the caller and passed in (documented "to avoid duplicate computation") — keep that contract if you port either side. (3) Allowlist variation is additive/subtractive composition at ONE function, never scattered conditionals — every environment-dependent deviation is visible in a single grep target. (4) Cross-shell sharing means a fix to git's flag table automatically patches both tools; duplicating tables per-shell would have left the PS side vulnerable to every differential in this plane.

**Probe:** no upstream tests reachable — coverage caveat. Pins from repo root: `grep -nF "behavior === 'allow'" src/tools/BashTool/BashTool.tsx` → :440; consumer wiring `grep -nF "checkSedConstraints(input, toolPermissionContext)" src/tools/BashTool/bashPermissions.ts` → :1142; shared-map reuse: `grep -nF "validateFlags" src/tools/PowerShellTool/readOnlyValidation.ts` → :28,:1700,:1726.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getCommandAllowlist", limit: 4 });
// → getCommandAllowlist :1201-1215 line-exact rank #1
```

## Verdict
Adopt the single-verdict-two-consumers wiring and centralized allowlist composition. Adapt USER_TYPE gating to your own tier system. Omit the ant-only block unless your deployment has internal CLIs.
