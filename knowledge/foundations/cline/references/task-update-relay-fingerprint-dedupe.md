<!-- capsule-v2 -->
# Task-update relay fingerprint dedupe — how do you push out-of-band team progress to chat threads without spamming duplicates or noise?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How does a connector relay hub team-progress projections to the right chat thread exactly once per meaningful change, and which events are suppressed as noise?

## Fingerprint-gated, session-routed progress relay
**Path/Symbol:** `apps/cli/src/connectors/task-updates.ts:startConnectorTaskUpdateRelay` (:136-223), `formatConnectorTaskUpdate` (:53-103), `createTaskUpdateFingerprint` (:124-134), `findBindingForSessionId` (:105-122).
**Signature:** `startConnectorTaskUpdateRelay<TState>(input: { client; clientId; bot; logger; bindingsPath; transport; postToThread? }): () => void` (returns the unsubscribe stopper); `createTaskUpdateFingerprint(event: TeamProgressProjectionEvent): string`.
**Data Shape:** In: `TeamProgressProjectionEvent` {sessionId, summary (teamName, tasks/runs byStatus counts, updatedAt), lastEvent {eventType, runId?, taskId?, message?}}. State: one `lastSentBySession: Map<sessionId, fingerprint>` per relay instance.

### Decisive source
```ts
const body = formatConnectorTaskUpdate(event);
if (!body) {
	return; // unknown event type, or team_task_updated with nothing in progress
}
const fingerprint = createTaskUpdateFingerprint(event);
if (lastSentBySession.get(event.sessionId) === fingerprint) {
	return; // exact repeat, drop BEFORE any binding lookup
}
const match = findBindingForSessionId(readBindings<TState>(input.bindingsPath), event.sessionId);
if (!match?.binding.serializedThread) {
	return;
}
lastSentBySession.set(event.sessionId, fingerprint);
```

**Flow:** `client.streamTeamProgress({clientId: \`\${clientId}-task-updates\`}, ...)` — a distinct subscription identity per concern (the schedule stream uses `-server-events`) → format: seven event types map to chat lines (`run_started/progress/completed/failed/cancelled/interrupted`, `team_task_updated`); unknown types AND `team_task_updated` with `in_progress <= 0` return undefined (noise gate) → fingerprint = JSON of {eventType, runId, taskId, message, summary.updatedAt}; exact repeats dropped before disk I/O → route by sessionId against BOTH binding slots (`binding.sessionId` OR `binding.state.sessionId`) → deliver via the injected `postToThread` (adapter-specific: token-scoped + invalid_thread_ts reaping on Slack) or plain `thread.post`; delivery failures log warn and never throw → fingerprint is recorded only after a binding match, so a not-yet-bound session retries on the next projection.
**Invariant:** (1) At most one send per (session, fingerprint) — replays and re-projections of unchanged state are silent. (2) The relay is transport-neutral: the ONLY adapter-specific code is the injected `postToThread`. (3) Suppression never loses the LATEST state: a changed message or updatedAt produces a new fingerprint. (4) Hook sibling: `dispatchConnectorHook` (hooks.ts :17-64) observes message.received/completed/failed via `$SHELL -lc`, warn-logs and swallows failures — hooks observe, never gate; `authorizeConnectorEvent` (:66-143) is the gate twin and is deliberately fail-OPEN (zod action default "allow"; every failure path — non-zero exit, parseError, non-JSON stdout, dispatch throw — falls through to allow), the exact opposite of the ACP permission plane's fail-closed.
**Probe:** `apps/cli/src/connectors/task-updates.test.ts` — "finds a binding by session id in either binding slot", "formats run progress updates for chat delivery" (byte-exact three-line body), "suppresses generic task update noise when nothing is in progress" (undefined), "changes the fingerprint when the progress payload changes".

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", file: "apps/cli/src/connectors/task-updates.ts", symbol: "startConnectorTaskUpdateRelay" });
```

## Verdict
Adopt the relay shape: per-concern subscription identity, format-or-suppress, fingerprint dedupe before disk I/O, dual-slot session routing, adapter injection only at the post boundary. Adapt the event vocabulary and fingerprint fields to the host's projection schema. Omit the fail-open authorize twin if the host has no external authorization hook — and never reuse its fail-open default for security-sensitive gates. Coverage caveat: formatting/dedupe/routing are test-pinned; the relay's stream wiring and hooks.ts have no dedicated suite (source-read evidence at the pin).
