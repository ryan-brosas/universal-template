<!-- capsule-v2 -->
# acp-session-manager-lifecycle — how do you keep a lazily-created agent session identity-stable across prompts, resumes, and provider switches without losing the conversation?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When is the runtime session created, how does the client-held id survive restarts, and what preserves history across teardown?

## Lazy idempotent manager; core session persisted UNDER the client-held id; save-messages-before-teardown; one AbortController cancel state machine; cancelled never surfaces as error
**Path/Symbol:** `apps/cli/src/acp/acpAgent.ts` (`ensureSessionManager` :689-759, `teardownSessionManager` :662-687, `prompt` :325-400, `cancel` :402-416, `shutdown` :601-615, `loadSession` :243-297).
**Signature:** `ensureSessionManager(session: SessionState, acpSessionId: string, options?: { resume?: boolean }): Promise<MessageWithMetadata[] | undefined>` — returns early when a manager already exists.
**Data Shape:** `SessionState` carries `sessionManager?`, `activeSessionId?`, `abortController?`, `unsubscribe?`, `fatalError?`, `pendingInitialMessages?`. The approval capability closes over the connection: `session.autoApproveTools ? Promise.resolve({approved:true}) : requestAcpToolApproval(this.conn, acpSessionId, request)`.

### Decisive source
```ts
const started = await sessionManager.start({
	source: SessionSource.CLI,
	config: { ...config, modelId: session.currentModelId,
		// Persist the core session under the ACP session id so that
		// session/load can find the conversation by the id the client holds.
		sessionId: acpSessionId },
	interactive: true, initialMessages,
});
// resume path — fail closed:
if (!initialMessages || initialMessages.length === 0) {
	await sessionManager.dispose("acp_load_session_not_found").catch(() => {});
	throw RequestError.resourceNotFound(acpSessionId);
}
// teardown preserves continuity — read BEFORE abort/dispose:
session.pendingInitialMessages =
	await session.sessionManager.readMessages(session.activeSessionId);
```

**Flow:** first prompt/load ⇒ ensureSessionManager builds createCliCore with the connection-closing approval capability ⇒ resume reads messages under the ACP id (empty ⇒ dispose + resourceNotFound; loadSession also deletes the half-built session state on throw) ⇒ non-resume consumes pendingInitialMessages ONCE (immediately `= undefined`) ⇒ subscribeToAgentEvents stashes `event.type==="error" && !recoverable` as fatalError (Error-ified via describeAgentError because the runtime re-wraps errors across the event boundary, breaking instanceof) ⇒ start() persists under the client-held id. Cancel: controller stored BEFORE async init, aborted re-checked before AND after ensureSessionManager ("Re-check after async initialization" — cancel-before-prompt wins ⇒ stopReason cancelled); onAbort listener (once:true) forwards sessionManager.abort swallow-caught; finally clears the controller. A cancelled turn ALWAYS reports cancelled (spec forbids surfacing cancellations as errors), so the stashed fatalError throws only when stopReason ≠ cancelled. teardownSessionManager (provider/org switch) saves messages BEFORE abort/unsubscribe/dispose("provider_change"); shutdown() aborts every controller, unsubscribes, abort+dispose("acp_shutdown") each manager, clears the map.
**Invariant:** The client-held session id is the durable identity across processes; a manager is created at most once per session state; teardown never loses conversation history; a cancelled turn never reports an error; a fatal error always fails the turn unless it was cancelled.
**Probe:** `grep -cF 'dispose("acp_load_session_not_found")' apps/cli/src/acp/acpAgent.ts` → 1; `grep -cF 'dispose("provider_change")' apps/cli/src/acp/acpAgent.ts` → 1; `grep -cF 'sessionId: acpSessionId,' apps/cli/src/acp/acpAgent.ts` → 1; `grep -cF 'Re-check after async initialization' apps/cli/src/acp/acpAgent.ts` → 1; `grep -cF 'stopReason !== "cancelled"' apps/cli/src/acp/acpAgent.ts` → 1; `grep -cF 'session.pendingInitialMessages = undefined' apps/cli/src/acp/acpAgent.ts` → 1. NO dedicated AcpAgent suite exists (coverage caveat) — behavior anchored by the five sibling suites + direct whole-file read.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "ensureSessionManager teardownSessionManager pendingInitialMessages acp_load_session_not_found", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy idempotent session managers, persisting the runtime session under the client-held id, save-before-teardown continuity, one-AbortController cancel with double re-check, cancelled-not-error reporting, and fail-closed empty-resume. Adapt the dispose reason vocabulary and the approval-capability closure to your runtime. Omit Cline's provider-settings persistence. Coverage: source read whole at pin; no direct suite — recorded caveat.

