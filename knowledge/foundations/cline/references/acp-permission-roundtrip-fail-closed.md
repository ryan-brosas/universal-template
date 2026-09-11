<!-- capsule-v2 -->
# acp-permission-roundtrip-fail-closed — how does a tool-approval round-trip stay fail-closed across every abnormal transport path?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When the approval client can cancel, throw, or answer with an unknown option, what does the tool call do — and why is "allow always" a dead affordance?

## Pending-frame-then-request; closed decision table defaulting to deny; decision always echoed; auto-approve bypass closes over the connection
**Path/Symbol:** `apps/cli/src/acp/permissions.ts` (`translateToolToPermissionRequest` :31-49; `handlePermissionResponse` :57-83; `requestAcpToolApproval` :90-132) + `apps/cli/src/acp/acpAgent.ts` :703-706 (capability wiring).
**Signature:** `requestAcpToolApproval(conn: AgentSideConnection, sessionId: string, request: ToolApprovalRequest): Promise<ToolApprovalResult>` — `{approved: boolean, reason?: string}`.
**Data Shape:** PERMISSION_OPTIONS trio: `allow_once` / `allow_always` / `reject_once`. Tool identity rides `tool-utils.ts`'s dual-vocabulary `TOOL_KIND_MAP` (vscode-style AND sdk-style snake_case names → ACP's nine kinds; unknown ⇒ "other" fail-soft) and `buildToolTitle` (`toolName: summary`, bare name when no summary).

### Decisive source
```ts
void conn.sessionUpdate({ sessionId, update: { …permissionRequest.toolCall,
	sessionUpdate: "tool_call_update" } });            // pending frame, fire-and-forget
try { response = await conn.requestPermission(permissionRequest); }
catch { return { approved: false, reason: "Permission request failed" }; }  // transport throw ⇒ DENY
// decision table: cancelled ⇒ deny "Permission request was cancelled";
// allow_once|allow_always ⇒ approve; reject_once|reject_always ⇒ deny;
// default ⇒ deny `Unknown permission option: ${optionId}`   (fail-closed)
void conn.sessionUpdate({ …, update: { sessionUpdate: "tool_call_update",
	toolCallId: request.toolCallId, status: result.approved ? "in_progress" : "failed" } });
```

**Flow:** translate (pending tool_call frame with title/kind/rawInput) ⇒ emit pending update (`void`, never awaited into the runtime) ⇒ await requestPermission ⇒ map outcome through the closed table ⇒ ALWAYS emit the decision frame (approved ⇒ "in_progress", denied ⇒ "failed") ⇒ return the result. The capability is wired in `ensureSessionManager` :703-706 closing over the connection: `session.autoApproveTools ? Promise.resolve({approved:true}) : requestAcpToolApproval(this.conn, acpSessionId, request)`; the auto-approve toggle parses boolean OR legacy string forms and is `undefined` (reject) otherwise.
**Invariant:** Every abnormal path denies: cancelled, transport throw, and unknown optionId all yield `{approved:false}` with a reason — silence never approves. `allow_always` is a DEAD AFFORDANCE at this pin: grep-proven, it appears ONLY in permissions.ts across apps/cli/src and NOWHERE in sdk/packages — nothing persists an always-rule, so it collapses to allow-once at this boundary.
**Probe:** `grep -cF 'return { approved: false, reason: "Permission request failed" };' apps/cli/src/acp/permissions.ts` → 1; `grep -cF 'reason: `+backtick+`Unknown permission option: ${optionId}`+backtick+`,' apps/cli/src/acp/permissions.ts` → 1; `grep -cF 'requestAcpToolApproval(this.conn, acpSessionId, request)' apps/cli/src/acp/acpAgent.ts` → 1; `grep -rn "allow_always" apps/cli/src` → 3 hits, all permissions.ts; `grep -rn "allow_always" sdk/packages` → 0 hits. Coverage caveat: permissions.ts has NO dedicated suite — behavior anchored by the acpAgent capability wiring (read directly :689-759) and the auto-approve suite (`auto-approve.test.ts`, 6 cases, read whole: booleans, legacy string forms, fail-closed undefined for "yes"/1/null/undefined).

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.apps.cli.src.acp.permissions.requestAcpToolApproval" });
```

## Verdict
Adopt the fail-closed decision table with an always-echoed decision frame, fire-and-forget pending updates, and the auto-approve bypass as a capability closure over the connection. Adapt the option vocabulary and tool-kind map to host tool names. Omit (or deliberately implement) the always-rule persistence Cline itself lacks — do not port the dead affordance as if it were durable. Coverage: sources read whole at pin; no dedicated permissions suite; MCP coverage check not runnable this session — recorded caveat.
