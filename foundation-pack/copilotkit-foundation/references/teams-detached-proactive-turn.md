<!-- capsule-v2 -->
# teams-detached-proactive-turn

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-teams/src/adapter.ts`
- Symbol: `TeamsAdapter.handleActivity / runDetached / withProactive / canGoProactive / startTypingHeartbeat`
- Lines: handleActivity :131-282, runDetached :378-385, withProactive :388-399, canGoProactive :368-370, heartbeat :731-735
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-teams.src.adapter.TeamsAdapter.runDetached`

## Question
The Teams channel holds the inbound HTTP turn open while the bot works — how does a run that must SUSPEND for minutes at a HITL card click avoid pinning that turn (and why does the same fork exist for interactions)?

## Signature & Data Shape
```typescript
canGoProactive(): boolean;                       // true iff an M365 app id is configured
runDetached(reference: Partial<ConversationReference>, fn: (ctx: TurnContext) => Promise<void>): void;
withProactive(reference, fn): Promise<void>;     // cloud.continueConversation(appId, reference, ctx => fn(ctx))
startTypingHeartbeat(t): () => void;             // immediate ping + setInterval 3500ms; returns stop fn
readonly ackDeadlineMs = 15000;
```

## Decisive Source Excerpt
```typescript
if (this.canGoProactive()) {
  // Credentialed (real Teams): ack the turn now and run on a detached
  // proactive context so HITL's `awaitChoice` can suspend the run for
  // minutes without holding the HTTP turn open.
  this.runDetached(reference, (proactive) =>
    drive({ conversationKey, reference, context: proactive }));
} else {
  // Anonymous/local (M365 Playground): `continueConversation` needs an app
  // id we don't have, so run on the inbound turn context. The localhost
  // connection stays open across an `awaitChoice` suspend until the click.
  try { await drive({ conversationKey, reference, context }); } catch (err) { ... }
}
```
The SAME fork guards interaction handling (:180-196): a credentialed card click's inbound connector client is created with an ANONYMOUS identity, so editing the picker card in place (`updateActivity`, a PUT to the Connector) is rejected 401 — the interaction is re-run on a detached app-id-authenticated proactive context and the click is acked immediately.

## Flow
1. Inbound activity → normalize → **ack the HTTP turn immediately**, hand work to `runDetached`.
2. Detached leg opens its own stable `TurnContext` via `continueConversation`; the whole agent run (including multi-minute `awaitChoice` suspension) streams on it.
3. Errors are logged, never surfaced to the inbound turn (`void …catch(log)`); one bad turn cannot become an unhandled-rejection crash loop (the SDK's own `onTurnError` is also contained at :110-112).
4. While work runs, typing is a HEARTBEAT not a ping: Teams' indicator lapses after seconds, so `setInterval(3500)` re-sends until the run resolves; the stop fn runs in `finally` so the timer always clears.
5. Inbound file attachments are downloaded inside `drive` AFTER the ack (:207-239) so a slow download never blocks intake, and multimodal content lands in the transcript (a follow-up "now make it a bar chart" still sees the CSV).

## Invariant
Never hold the inbound HTTP turn across a suspend point; every out-of-turn write must go through an app-id-authenticated proactive context (anonymous contexts can read but their writes 401), and background timers/legs must be contained (stop-fn in finally, fire-and-forget catches) so failure stays per-turn.

## Direct-Test Probe
- File: `packages/channels-teams/src/adapter.test.ts`
- Lines: :52 interaction routes through authenticated proactive context when credentialed; :89 anonymous mode uses inbound context; :138 uploaded CSV becomes a content part; :235 typing heartbeat sends immediately, repeats, stops when cleared

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"TeamsAdapter runDetached continueConversation proactive","limit":10}'
```

## Verdict
Adopt ack-immediately/detach-via-conversation-reference + the credential-gated dual path + the typing heartbeat. Adapt the resume primitive (continueConversation → your platform's conversation-reference replay). Omit the Playground-only in-turn fallback only if you never run without credentials.
