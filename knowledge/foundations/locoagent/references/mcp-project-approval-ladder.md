<!-- capsule-v2 -->
# Project-server approval ladder — when does .mcp.json auto-approve, and why can't a repo approve bypass mode on the user's behalf?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What decides approved/rejected/pending for project-scope MCP servers across interactive, non-interactive, and bypass-permissions modes?

## Explicit lists → enableAll → bypass (settings-source-restricted) → non-interactive → pending
**Path/Symbol:** `src/services/mcp/utils.ts`:`getProjectMcpServerStatus` (:351-406); consumers filter projectServers to `'approved'` before merge (config.ts :1164-1170).
**Signature:** `(serverName: string): 'approved' | 'rejected' | 'pending'`; all name comparisons run through normalizeNameForMCP on BOTH sides (:355,:361,:369).
**Data Shape:** inputs: settings.disabledMcpjsonServers / enabledMcpjsonServers / enableAllProjectMcpServers; `hasSkipDangerousModePermissionPrompt()` reads userSettings/localSettings/flagSettings/policySettings but NOT projectSettings.

### Decisive source
```ts
// SECURITY: We intentionally only check skipDangerousModePermissionPrompt via
// hasSkipDangerousModePermissionPrompt(), which reads from userSettings/localSettings/
// flagSettings/policySettings but NOT projectSettings (repo-level .claude/settings.json).
// This is intentional: a repo should not be able to accept the bypass dialog on behalf of
// users. We also do NOT check getSessionBypassPermissionsMode() here because
// sessionBypassPermissionsMode can be set from project settings before the dialog is shown,
// which would allow RCE attacks via malicious project settings.  (:376-385)
if (getIsNonInteractiveSession() && isSettingSourceEnabled('projectSettings')) {
  return 'approved'   // SDK/-p mode: explicit mode choice + projectSettings opt-in required
}
return 'pending'
```

**Flow:** rejected if explicitly disabled (normalized compare) → approved if enabled-listed or enableAllProjectMcpServers → in bypass-permissions mode approved ONLY when the bypass came from user-level sources AND projectSettings source is itself enabled → non-interactive sessions auto-approve under the same source-enabled guard → else pending (UI must ask). The TODO at :357 records that removing the `?.` breaks an e2e test — keep defensive access.
**Invariant:** A repository can never grant itself execution trust via its own settings file: every auto-approve path requires either an explicit per-user list or a user-level bypass flag plus projectSettings being enabled. Normalization must apply to both sides or case/dot variants dodge the deny list.
**Probe:** `grep -n 'hasSkipDangerousModePermissionPrompt() &&' src/services/mcp/utils.ts` (`387:`) and `grep -n 'getIsNonInteractiveSession() &&' src/services/mcp/utils.ts` (`399:`) and `grep -n 'enableAllProjectMcpServers' src/services/mcp/utils.ts` (`371:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getProjectMcpServerStatus", limit: 5 });
```

## Verdict
Adopt the ladder order and the repo-cannot-self-approve security invariant. Adapt settings-source names. Omit e2e-test commentary beyond the defensive-access note.
