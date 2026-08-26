<!-- capsule-v2 -->
# Sandbox auto-allow coupling — sandboxed Bash skips the tool-level ask rule, and `!` bash-mode always runs unsandboxed

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does "sandboxed ⇒ auto-approve" compose with the permission ladder without letting excluded or override commands slip past prompts?

## Permission-ladder coupling
**Path/Symbol:** `src/utils/permissions/permissions.ts` : `canSandboxAutoAllow` (:1094-1100 in checkPathSafety ladder twin; identical block :1189-1195 in hasPermissionsToUseToolInner 1b); `src/tools/BashTool/shouldUseSandbox.ts` as the third conjunct's implementation.
**Signature:** `canSandboxAutoAllow = tool.name === BASH_TOOL_NAME && SandboxManager.isSandboxingEnabled() && SandboxManager.isAutoAllowBashIfSandboxedEnabled() && shouldUseSandbox(input)`.
**Data Shape:** four-way AND — tool identity, global enablement, user opt-in (`sandbox.autoAllowBashIfSandboxed`, default TRUE), and per-input verdict.

### Decisive source
```ts
// When autoAllowBashIfSandboxed is on, sandboxed commands skip the ask rule and
// auto-allow via Bash's checkPermissions. Commands that won't be sandboxed (excluded
// commands, dangerouslyDisableSandbox) still need to respect the ask rule.
const canSandboxAutoAllow =
  tool.name === BASH_TOOL_NAME &&
  SandboxManager.isSandboxingEnabled() &&
  SandboxManager.isAutoAllowBashIfSandboxedEnabled() &&
  shouldUseSandbox(input)
if (!canSandboxAutoAllow) {
  return { behavior: 'ask', decisionReason: { type: 'rule', rule: askRule }, ... }
}
```

**Flow:** When a whole-tool ASK rule exists for Bash, the ladder consults this AND before prompting: true ⇒ fall through to command-specific rules inside Bash's own checkPermissions (deny rules and content-specific asks STILL fire there — auto-allow never overrides a deny); false (any conjunct) ⇒ prompt. The same verdict feeds scheduling elsewhere via the shared helper, so the sandbox decision is made ONCE per input. Complement: `!` user-initiated bash-mode commands pass `dangerouslyDisableSandbox: true` explicitly (`src/utils/processUserInput/processBashCommand.tsx` :78-79, both PowerShellTool and BashTool call sites) — honored only because `allowUnsandboxedCommands` defaults true; on Windows-native shouldUseSandbox returns false regardless (unsupported platform).

**Invariant:** (1) Auto-allow is gated on shouldUseSandbox(input), not on enablement alone — an excluded command must PROMPT even though sandboxing is generally on, because it will run OUTSIDE the fence. This is the exact inverse of the exclusion ladder's "not a security boundary" stance: convenience for the user, but the permission layer treats unsandboxed execution as prompt-worthy. (2) The four-conjunct order matters for cost: cheap string comparisons first, memoized manager predicates before the per-input parse. (3) Default-true `autoAllowBashIfSandboxed` makes sandbox adoption silently change UX — porters flipping defaults must document it.

**Probe:** anchored at the locoagent repo root — `grep -n 'canSandboxAutoAllow' src/utils/permissions/permissions.ts | head -2` → :1094,:1100; `grep -c 'canSandboxAutoAllow =' src/utils/permissions/permissions.ts` → 2; `grep -cn 'dangerouslyDisableSandbox: true' src/utils/processUserInput/processBashCommand.tsx` → 2; `grep -n 'run outside sandbox' src/utils/processUserInput/processBashCommand.tsx` → :68.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "wrapWithSandbox isAutoAllowBashIfSandboxedEnabled permissions", limit: 5 });
```

## Verdict
Adopt the four-way AND with shouldUseSandbox as the deciding conjunct, and deny-rules-still-fire-under-auto-allow. Adapt default values to your product's trust model but keep excluded-commands-prompt. Omit bash-mode UX specifics. Coverage caveat: no upstream unit tests; probes pin both ladder sites line-exact.
