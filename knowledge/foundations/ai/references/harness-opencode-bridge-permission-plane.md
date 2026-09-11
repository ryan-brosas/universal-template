<!-- capsule-v2 -->
# OpenCode bridge permission plane — how do you answer a sandboxed agent's native permission prompts from host policy without letting it touch files outside the workspace?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The runtime has its OWN permission system and will ask before every sensitive action. The bridge must answer those asks automatically from host policy (permission mode + builtin-tool filtering) — how is the decision ladder ordered, and where does each class of action end up?

## Config-side demotion, then event-side answering
**Path/Symbol:** `packages/harness-opencode/src/bridge/index.ts` — `buildOpenCodeConfig` permission block (:220–250), `resolveInactiveBuiltinToolNames` (:1090–1100), `isBuiltinToolInactive` (:1102–1110), `handlePermissionV2` (:931–969), `handlePermission` (:971–1009), `selectPermissionReply` (:1011–1072), `toPermissionToolName` (:1074–1088), `TOOL_KIND` (:103–115), `isExternalPath` (:1112–1119), `isPathInsideOrEqual` (:1121–1124).
**Signature:** `selectPermissionReply({action, resources, requestID, toolCallId, permissionMode, builtinToolFiltering, turn, emit}): Promise<{reply: 'once' | 'always' | 'reject'; message?: string}>`.
**Data Shape:** default config permissions: read/glob/grep/list `'allow'`; edit/bash/external_directory/webfetch/doom_loop/task `'ask'`. Inactive builtins (allow-mode ⇒ every PUBLIC_TO_NATIVE key NOT in the filter list; deny-mode ⇒ the listed names) are demoted to `'ask'` so the runtime ASKS instead of executing. Reply vocabulary: `'once'` / `'always'` / `'reject'` (+ optional message). TOOL_KIND: read/glob/grep/ls/webfetch=readonly; write/edit/skill/todowrite=edit; bash/agent=bash.

### Decisive source
```ts
// index.ts:1030–1058 — ladder order: external path REJECT first, then
// inactive-builtin host approval, then mode auto-allow, then host approval
const toolName = toPermissionToolName(action);
if (resources.some(resource => isExternalPath(resource))) {
  return { reply: 'reject', message: 'External directory access rejected.' };
}
if (
  isBuiltinToolInactive({ toolName, toolFiltering: builtinToolFiltering })
) {
  emit({ type: 'tool-approval-request', approvalId: requestID, toolCallId });
  const decision = await turn.requestToolApproval(requestID);
  return decision.approved
    ? { reply: 'once' }
    : { reply: 'reject', ...(decision.reason ? { message: decision.reason } : {}) };
}
if (!permissionMode || permissionMode === 'allow-all') {
  return { reply: 'always' };
}
const kind = TOOL_KIND[toolName] ?? 'bash';
const allowed =
  permissionMode === 'allow-edits'
    ? kind === 'readonly' || kind === 'edit'
    : kind === 'readonly';
if (allowed) return { reply: 'always'; }
```
```ts
// index.ts:1112–1119 — external = absolute AND outside workdir AND outside
// skillsDir; relative paths are never "external"
function isExternalPath(resource: string): boolean {
  if (!path.isAbsolute(resource)) return false;
  const normalized = path.resolve(resource);
  return (
    !isPathInsideOrEqual(normalized, workdir) &&
    (!skillsDir || !isPathInsideOrEqual(normalized, skillsDir))
  );
}
```

**Flow:** at runtime start, inactive builtins are demoted to `'ask'` in the generated config (so a filtered-out builtin cannot execute silently — it must ask) → the event loop intercepts `permission.v2.asked` (action + resources + source.callID) and legacy `permission.asked` (permission + patterns + tool.callID) BEFORE any other translation → `selectPermissionReply` runs the ladder: (1) any resource outside workdir+skillsDir ⇒ hard reject with a message; (2) inactive builtin ⇒ emit `tool-approval-request` and await `turn.requestToolApproval(requestID)` — approved ⇒ `'once'`, denied ⇒ `'reject'` carrying the host's reason; (3) no mode or allow-all ⇒ `'always'`; (4) allow-edits admits readonly+edit kinds, the default mode admits readonly only, unknown kinds classify as `'bash'` (most conservative); (5) everything else goes to host approval. The reply is sent back through the version-matched endpoint (`client.v2.session.permission.reply` vs `client.permission.reply` with `directory`). Action strings normalize by substring match (`bash|shell→bash`, `task|agent→agent`, …) because the runtime's action vocabulary is not stable.
**Invariant:** an out-of-workspace path is rejected BEFORE any policy or human can approve it (the reject rung precedes the approval rungs); a filtered-out builtin always costs a host approval even under allow-all; unknown tool kinds fail toward the restrictive side (`?? 'bash'`).
**Probe:** none direct — NO test pins the permission ladder (index.test.ts mocks `requestToolApproval` but never drives a permission event). Deterministic-read-only; the config-side demotion and both handlers were read whole-file at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "selectPermissionReply handlePermissionV2 isExternalPath resolveInactiveBuiltinToolNames", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-sided design for any runtime with native permissions: demote filtered tools to "ask" in CONFIG (defense in depth — the runtime must ask) AND answer asks from host policy in the EVENT LOOP; adopt the rung order hard-reject → filtered-needs-human → mode-auto-allow → human, because a security reject that a human could override is a hole; adopt substring action normalization plus a conservative default kind for unstable vendor vocabularies. Adapt the mode set, kind table, and reply vocabulary to your runtime; omit the skillsDir carve-out unless you materialize extra readable roots. Caveat: deterministic-read-only — no test drives a permission event through the bridge.
