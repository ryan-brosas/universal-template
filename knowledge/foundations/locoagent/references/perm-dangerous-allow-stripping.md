<!-- capsule-v2 -->
# Dangerous allow-rule stripping — interpreter prefixes that bypass a classifier, stashed for restore

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** If an auto-approval classifier vets each action, which pre-granted ALLOW rules silently defeat it, and how do you remove them at mode entry without losing the user's config?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/permissionSetup.ts` — `isDangerousBashPermission` five-shape matcher (:94-147), `isDangerousPowerShellPermission` + `.exe` variants (:157-233), `isDangerousTaskPermission` ANY-Agent-allow (:240-245), `findDangerousClassifierPermissions` incl. `--allowed-tools` CLI scan (:295-342), `removeDangerousPermissions` source-grouped removal (:472-503), `stripDangerousPermissionsForAutoMode` stash-on-strip (:510-553), `restoreDangerousPermissions` clear-once (:561-579); `src/utils/permissions/dangerousPatterns.ts` — `CROSS_PLATFORM_CODE_EXEC` shared list (:18-42), ant-only empirical tail (:58-79).
**Signature:** `isDangerousBashPermission(toolName: string, ruleContent: string | undefined): boolean`.
**Data Shape:** Dangerous = tool-level allow (no content), standalone `*`, exact pattern, `pat:*`, `pat*`, `pat *`, or `pat -*…*` — five shapes per pattern; PS adds `.exe` first-word variants (`npm.exe run:*`).

### Decisive source
```ts
// Check for patterns like "python -*" which would match "python -c 'code'"
if (content.startsWith(`${lowerPattern} -`) && content.endsWith('*')) {
  return true
}
```

**Flow:** at auto-mode ENTRY (`transitionPermissionMode`) → re-scan all allow rules from every source plus CLI specs → classify dangerous via Bash list ∪ PS list (shared CROSS_PLATFORM_CODE_EXEC prevents drift) ∪ any Agent-tool allow (delegation attack prevention) → group by destination → `removeRules` per destination → STASH what was actually removed in `context.strippedDangerousRules`, filtered to persistable destinations so stash == removed → on EXIT, re-add from stash and clear it (second exit is a no-op). The same predicates run in the step ladder's auto branch so PowerShell prefix rules are stripped before classification.

**Invariant:** (1) An allow rule is a CLASSIFIER BYPASS: `Bash(python:*)` lets arbitrary code through without evaluation — stripping must happen BEFORE the classifier runs, not after. (2) Stash must mirror EXACTLY what was removed (same destination filter), or restore resurrects rules into sources they were never in / loses them. (3) Pattern matching is shape-exact, not substring: `'gh api'` is separate from `'gh'` because `gh api:*` does not match the bare `gh` entry — enumerate compound commands explicitly. (4) Matching lowercases both sides; PS aliases (`iex`/`icm`/`saps`/`nsn`/`etsn`) and .NET escapes (`add-type`, `new-object`) are enumerated, not pattern-guessed. (5) Re-entry after a mid-session disk reload must RE-strip: `syncPermissionRulesFromDisk` re-adds dangerous rules without touching the stash (`transitionPlanAutoMode`, :1516-1521).

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF 'lowerPattern} -' src/utils/permissions/permissionSetup.ts` → :141; `grep -nF "Mirror removeDangerousPermissions' source filter" src/utils/permissions/permissionSetup.ts` → :541; `grep -nF 'CROSS_PLATFORM_CODE_EXEC,' src/utils/permissions/permissionSetup.ts` → :65; graph search `stripDangerousPermissionsForAutoMode` → permissionSetup.ts :510-553 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isDangerousBashPermission findDangerousClassifierPermissions DANGEROUS_BASH_PATTERNS", limit: 8 });
```

## Verdict
Adopt the five-shape dangerous-rule matcher, shared cross-platform lists, any-agent-allow-is-dangerous, and stash==removed strip/restore pairing. Adapt the pattern lists to your interpreters and shells. Omit the ant-only empirical tail (`coo`, `fa run`) unless your host has the same tools.
