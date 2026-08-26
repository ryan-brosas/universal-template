<!-- capsule-v2 -->
# discord-interaction-ack-race

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-discord/src/pending-interactions.ts` (+ consumer `adapter.ts:277-324`)
- Symbol: `PendingInteractions.register / respondWith / settle`
- Lines: pending-interactions.ts whole (~60L); adapter wiring :210-220, :277-281, :286-303
- Commit: `e9387e04835545c45744b791aee7c9c03520be31` (= base_sha)
- Graph Node: `ext-copilotkit.packages.channels-discord.src.pending-interactions.PendingInteractions.respondWith`

## Question
How does a Discord bot ack an interaction within Discord's hard 3-second window when the real handler may take longer — without double-acking or blocking a handler that wants to open a modal first?

## Signature & Data Shape
```typescript
export class PendingInteractions {
  constructor(opts: { ackBufferMs: number; defer: (i: LiveInteraction) => Promise<void> });
  register(interaction: LiveInteraction): string;          // arms auto-defer timer, returns triggerId
  respondWith(id: string, fn: (i) => Promise<void>): Promise<boolean>; // run fn FIRST if unresponded; true = won race
  settle(triggerId: string): Promise<void>;                // ack if still unresponded, then forget
}
```
Two registries exist per adapter, built in `start()`:
- `commandPending` — slash commands; its defer is `deferReply({ flags: MessageFlags.Ephemeral })` (a command's initial response is a reply, not a component update).
- `pending` — buttons/string-selects; its defer is plain `deferUpdate()`.
Both use `ackBufferMs = ackDeadlineMs - 500` (2500ms), leaving a ~500ms cushion inside Discord's 3000ms window.

## Decisive Source Excerpt
```typescript
register(interaction: LiveInteraction): string {
  const prev = this.entries.get(interaction.id);
  if (prev?.timer) clearTimeout(prev.timer);      // re-register ⇒ old timer dies ⇒ defer fires AT MOST ONCE
  const entry: Entry = { interaction, responded: false };
  entry.timer = setTimeout(() => void this.ack(entry), this.opts.ackBufferMs);
  this.entries.set(interaction.id, entry);
  return interaction.id;
}
async respondWith(triggerId, fn) {
  const entry = this.entries.get(triggerId);
  if (!entry || entry.responded) return false;    // lost the race — report, never throw
  entry.responded = true;                          // latch BEFORE awaiting fn
  if (entry.timer) clearTimeout(entry.timer);
  await fn(entry.interaction);
  return true;
}
```

## Flow
1. `interactionCreate` → `pending.register(i)` mints the triggerId and arms the 2.5s auto-defer.
2. The decoded event (with `triggerId`) is handed to `sink.onInteraction` so a handler may call `openModal` first — a modal MUST be an interaction's INITIAL response within ~3s.
3. `openModal` runs `respondWith(triggerId, showModal)`; winning cancels the timer and consumes the interaction's one initial response. It tries `pending` THEN `commandPending` (`shown = await pending.respondWith(...) || await commandPending.respondWith(...)`) because a triggerId belongs to exactly ONE registry — a slash-command modal silently fails if only `pending` is consulted (`adapter.ts:596-631`).
4. If the handler never responded, `settle(triggerId)` fires the fallback ack immediately after dispatch.
5. Every failure path still ends in an ack: decode throws and sink dispatch rejects are caught and logged so the event listener can't emit an unhandled rejection (`adapter.ts:296-302`); modal-submit acks branch on `i.isFromMessage()` — `deferUpdate` for component-origin modals, `deferReply(ephemeral)` for command-origin modals where `deferUpdate` would throw (`adapter.ts:310-322`).

## Invariant
Every live interaction receives EXACTLY ONE ack (timer, respondWith, or settle — whichever first wins the `responded` latch); a handler that needs the interaction's single initial response must win it via `respondWith` before the buffer window closes, and registry membership (component vs command) must be probed in order because ids are not globally unique across registries.

## Direct-Test Probe
- File: `packages/channels-discord/src/pending-interactions.test.ts`
- Lines: :20 auto-defers at deadline; :31 respondWith runs responder + cancels deferral; :47 returns false once already acked; :62 settle acks unresponded fast path; :73 re-register clears old timer (defer at most once)
- Also `packages/channels-discord/src/adapter.test.ts` :305 (modal from slash command acks deferReply) / :339 (from component acks deferUpdate) / :364 (openModal reaches commandPending)

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"PendingInteractions respondWith settle deferUpdate","limit":10}'
```

## Verdict
Adopt the timer-race ack pattern (buffer = platform deadline minus cushion, latched single-response arbitration, dual-registry probe order). Adapt the defer verb pair to the host's ack vocabulary. Omit nothing — the failure-swallowing catch blocks are load-bearing (Discord interactions expire and throw on late acks).
