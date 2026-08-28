<!-- capsule-v2 -->
# connector-session-reuse-recovery — how do you reuse a mapped runtime session safely when the mapping can be stale, terminal, or raced by a concurrent recovery?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When is a stored sessionId reusable, how often may a dead mapping be retried, and what stops an older failure from clearing a newer session?

## Fail open on missing status, reject terminal statuses, retry a dead mapping AT MOST ONCE, and CAS-guard every mapping clear
**Path/Symbol:** `apps/cli/src/connectors/session-runtime.ts` (`isReusableConnectorSession` :148-161, `TERMINAL_HUB_SESSION_STATUSES` :142-146, `getOrCreateSessionId` :166-296, `forgetThreadSession` :311-343, `runConnectorRuntimeTurnWithRecovery` in connector-host.ts :1093-1173).
**Signature:** `isReusableConnectorSession(session: { sessionId?: string; status?: string } | undefined | null): boolean`; `forgetThreadSession(input: { thread; bindingsPath; baseStartRequest; errorLabel; expectedSessionId: string }): Promise<boolean>`.
**Data Shape:** Hub session rows carry `sessionId` + optional `status`. Terminal set = {completed, failed, aborted, cancelled}. The retry latch `allowStaleSessionRetry` initializes to `params.staleSessionId === undefined` — a turn that already came through stale-steering recovery gets NO second retry.

### Decisive source
```ts
const status = session.status?.trim().toLowerCase();
if (!status) {
	// Older hubs omit status; treat presence as reusable and let send-time
	// session_not_found recovery handle true zombies.
	return true;
}
return !TERMINAL_HUB_SESSION_STATUSES.has(status);
```

**Flow:** `getOrCreateSessionId` loads the thread state; an existing sessionId is checked via `client.getSession` ⇒ reusable ⇒ persist + `session.reused` hook; terminal or missing ⇒ persist `sessionId: undefined` (warn log distinguishes "terminal" vs "missing") and start fresh ⇒ `startRuntimeSession` result is trimmed and empty-id throws ⇒ metadata update is best-effort (`.catch(() => undefined)`) BEFORE persisting the new mapping ⇒ the turn runner wraps `runConnectorRuntimeTurn` in a `for(;;)` loop: on `isUnusableSessionError` with the latch still open, it flips `allowStaleSessionRetry = false`, calls `forgetStaleThreadSession`, re-resolves a brand-new session, and replays the user's input once — a second failure rethrows instead of wedging the thread ⇒ `forgetThreadSession` is CAS-guarded: it clears ONLY when the stored id still equals `expectedSessionId` ("a newer session id must never be cleared by an older failure"). Wedged-run errors are caught by MESSAGE text because the hub's JSON boundary strips error classes.
**Invariant:** A terminal session is never reused; a status-omitting hub degrades to reuse-plus-send-time-recovery, never to a hard failure; a dead mapping is retried at most once per turn; a stale-id clear can never erase a concurrently recovered mapping.
**Probe:** `session-runtime.test.ts` (5 cases): "rejects missing and terminal sessions", "accepts live and status-omitted sessions"; `connector-host.test.ts`: "recovers from a stale thread session mapping by starting a new session". Probes: `grep -cF 'Older hubs omit status' session-runtime.ts` → 1; `grep -cF 'TERMINAL_HUB_SESSION_STATUSES' session-runtime.ts` → 2; `grep -cF 'a newer session id' session-runtime.ts` → 1; `grep -cF 'allowStaleSessionRetry = false' connector-host.ts` → 1; `grep -cF 'session_not_found' connector-host.ts` → 1.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "isReusableConnectorSession forgetThreadSession stale session retry session_not_found", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fail-open-on-missing-status with send-time backstop, the terminal-status set, the one-shot stale retry latch, and the expected-id CAS on mapping clears. Adapt the status vocabulary and `isUnusableSessionError` detection to your hub (note: match by message text if your RPC boundary strips error classes). Omit Cline's provider/OAuth key-resolution ladder in the same file. Coverage: session-runtime.ts read whole at pin (5-case suite, incl. one upstream-duplicated pair — noted); connector-host.ts recovery range read in whole-file context.
