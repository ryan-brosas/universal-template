<!-- capsule-v2 -->
# connector-active-turn-steering — how do you deliver a follow-up message into an already-running turn without forking sessions or announcing what did not happen?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How is an active turn found, steered, and — when the tracked session is dead — recovered without minting replacement sessions per racing message?

## Steer the active session silently; on a stale steer, delete only the attempted entry and enqueue recovery through the normal per-thread queue so racers line up behind
**Path/Symbol:** `apps/cli/src/connectors/connector-host.ts` (`handleUserTurn` steering block :1015-1087, `runConnectorRuntimeTurnWithRecovery` :1093-1173).
**Signature:** steering send: `client.sendRuntimeSession(activeTurn.sessionId, { config, prompt, attachments, delivery: "steer" }, { timeoutMs: null })`.
**Data Shape:** `activeTurns: Map<turnKey, ActiveConnectorTurn>` where `ActiveConnectorTurn = { sessionId, threadId, participantKey? }`. Lookup is two-rung: exact `turnKey` hit first, else a scan for an entry whose `sessionId` matches the thread's current mapped session AND `threadId` matches.

### Decisive source
```ts
} catch (error) {
	if (!isUnusableSessionError(error)) {
		throw error;
	}
	// Remove only the entry we attempted to steer, then route recovery
	// through the normal per-thread queue. Concurrent messages that saw
	// the same stale turn will line up behind this one instead of creating
	// independent replacement sessions.
	if (input.activeTurns?.get(activeTurnKey) === activeTurn) {
		input.activeTurns.delete(activeTurnKey);
	}
	await enqueueTurn(() =>
		runConnectorRuntimeTurnWithRecovery({
			input, runtimeInput, turnKey,
			staleSessionId: activeTurn.sessionId,
		}),
	);
	return;
}
// No acknowledgement: the follow-up is handed to the running session and its
// effect shows up in the answer. Announcing it added a line to every thread
// and overstated what happens, since the prompt is queued for the session
// rather than injected into the loop already running.
return;
```

**Flow:** after slash-command/mute/welcome gates, the host looks up an active turn (exact key, then sessionId+threadId scan — this is how steering reaches a session active under a DIFFERENT turn key) ⇒ found ⇒ build the user input and send with `delivery: "steer"` and `timeoutMs: null` (no hub command timeout) ⇒ success returns SILENTLY (in-source comment: announcing overstated what happens) ⇒ a stale steer (`isUnusableSessionError`) deletes ONLY the attempted entry under an identity check, then enqueues recovery through the normal per-thread turn queue with `staleSessionId` set — which also closes the retry latch inside the recovery runner (a turn that already came through stale-steering gets no second retry) ⇒ no active turn ⇒ straight to `runConnectorRuntimeTurnWithRecovery`.
**Invariant:** Concurrent messages observing the same stale active turn produce exactly ONE replacement session (they serialize behind the per-thread queue); a successful steer never posts an acknowledgement; the identity check prevents deleting a newer entry that replaced the stale one.
**Probe:** `connector-host.test.ts` (24 cases): "serializes concurrent recovery from the same stale active turn" (two racing stale steers ⇒ exactly one `startRuntimeSession`), "starts a new session when steering an active turn hits a dead session", "steers active Telegram turns without the hub command timeout", "steers when the same session is active under a different turn key". Probes: `grep -cF 'delivery: "steer"' connector-host.ts` → 1; `grep -cF 'overstated what happens' connector-host.ts` → 1; `grep -cF 'allowStaleSessionRetry = false' connector-host.ts` → 1; `grep -cF 'serializes concurrent recovery from the same stale active turn' connector-host.test.ts` → 1.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "activeTurns steer delivery sendRuntimeSession stale active turn recovery queue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt silent steering, the two-rung active-turn lookup, identity-checked single-entry deletion, and queue-routed recovery that serializes racers. Adapt the `delivery: "steer"` request field and `isUnusableSessionError` classification to your runtime. Omit Cline's chat-command gates that precede steering (covered by the host's command plane). Coverage: connector-host.ts read whole (three sequential reads) at pin; 24-case suite read whole.
