<!-- capsule-v2 -->
# Shadowed-rule detection — unreachable allow rules with sandbox-exception source semantics

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a user writes both `Bash` (ask) and `Bash(ls:*)` (allow), which rule wins, how do you TELL them their allow rule is dead, and when must the warning be suppressed?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/shadowedRuleDetection.ts` — `ShadowType` (:14), `UnreachableRule` (:19-25), `isSharedSettingSource` (:61-67), `isAllowRuleShadowedByAskRule` (:111-147), `isAllowRuleShadowedByDenyRule` (:160-184), `detectUnreachableRules` (:193-234).
**Signature:** `detectUnreachableRules(context: ToolPermissionContext, options: {sandboxAutoAllowEnabled: boolean}): UnreachableRule[]`.
**Data Shape:** `UnreachableRule = { rule, reason, shadowedBy, shadowType: 'ask'|'deny', fix }`; only SPECIFIC allow rules (ruleContent !== undefined) can ever be shadowed.

### Decisive source
```ts
// Special case: Bash with sandbox auto-allow from personal settings
// The sandbox exception is based on the ASK rule's source, not the allow rule's source.
if (toolName === BASH_TOOL_NAME && options.sandboxAutoAllowEnabled) {
  if (!isSharedSettingSource(shadowingAskRule.source)) {
    return { shadowed: false }
  }
  // Fall through to mark as shadowed - shared settings should always warn
}
```

**Flow:** for each allow rule → check deny-shadowing FIRST (more severe; a tool-wide deny makes specific allows truly blocked) → if deny-shadowed, `continue` so ask-shadowing is not also reported → else check tool-wide ask rules → Bash sandbox exception keyed on the ASK rule's source: personal sources (userSettings/localSettings/cliArg/session/flagSettings) don't warn because the user's own sandbox auto-allows; shared sources (projectSettings/policySettings/command — `isSharedSettingSource`) ALWAYS warn because teammates may lack sandbox. Fix suggestions name both the shadowing source and the shadowed source with concrete removal instructions.

**Invariant:** (1) Evaluation order in the real pipeline is deny → ask → allow, so a tool-wide deny/ask genuinely precedes a specific allow — the detector models precedence, not style preference. (2) The exception keys on the SHADOWING rule's source, not the allow rule's — a porter who reads the allow side produces wrong warnings. (3) Tool-wide vs tool-wide conflicts are deliberately NOT "shadowed" (both fire; first wins) — only specific-content allows get diagnostics. (4) One diagnostic per rule: deny beats ask in reporting.

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF "based on the ASK rule's source" src/utils/permissions/shadowedRuleDetection.ts` → :136; `grep -nF "source === 'projectSettings' ||" src/utils/permissions/shadowedRuleDetection.ts` → :63; `grep -nF "Don't also report ask-shadowing if deny-shadowed" src/utils/permissions/shadowedRuleDetection.ts` → :216; graph search `detectUnreachableRules` → :193-234 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "detectUnreachableRules isSharedSettingSource UnreachableRule", limit: 5 });
```

## Verdict
Adopt precedence-modeled shadow detection with per-source exception semantics and dual-sided fix text. Adapt which sources count as "shared" to your settings model. Omit nothing — this module is self-contained.
