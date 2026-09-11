<!-- capsule-v2 -->
# teams-streamed-by-edit-throttle

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-teams/src/message-stream.ts`
- Symbol: `TeamsMessageStream` / `scheduleFlush` / `finish`
- Lines: config :13-33, scheduleFlush :82-90, finish (final send fail-loud), DEFAULT_MIN_INTERVAL_MS = 700
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-teams.src.message-stream.TeamsMessageStream.scheduleFlush`

## Question
Teams has no native token streaming — how does a post-then-edit stream stay ordered and rate-limit-safe when edits arrive faster than the channel allows?

## Signature & Data Shape
```typescript
new TeamsMessageStream({
  post: (text) => Promise<string>,        // first send → activity id
  update: (id, text) => Promise<void>,    // subsequent edits
  finalize?: (id, text) => Promise<void>, // final edit through a priority lane
  typing?: () => Promise<void>,           // fired once before first post
  minIntervalMs?: number,                 // default 700
}).append(accumulatedText); const id = await finish();
```

## Decisive Source Excerpt
```typescript
// Edits are throttled (Teams rate-limits activity updates) and *serialised*
// through a per-message promise queue so an in-flight edit of "AL" can't be
// overtaken by a later edit of "ALPHA" and leave the message reading "AL".
private queue: Promise<void> = Promise.resolve();
private lastFlushedAt = 0;
private flushTimer: ReturnType<typeof setTimeout> | undefined;
```

## Flow
1. `append(text)` replaces the buffer view (callers pass ACCUMULATED text, not deltas — same discipline as discord/slack chunkers).
2. Flush scheduling is trailing-edge throttled: at most one edit per `minIntervalMs`, coalescing intermediate buffers (a burst of appends collapses into the latest text).
3. Every actual edit runs inside the per-message promise queue, so network in-flight edits cannot reorder — the classic "final message shows stale prefix" race dies here.
4. `finish()` cancels any pending throttled flush, drains the queue, then performs the FINAL send fail-loud (unlike interim edits); returns the activity id or `undefined` for an empty stream.
5. Adapter-side this is the whole streaming story: post first content, then keep editing that ONE message id (`adapter.stream()` :454-471) — no chunk fan-out like Discord.

## Invariant
Edits to one Teams activity are both rate-limited AND totally ordered (throttle + serialization are orthogonal halves; either alone leaves a visible corruption mode); the final buffer always wins via the fail-loud final flush.

## Direct-Test Probe
- File: `packages/channels-teams/src/message-stream.test.ts` (:135 lines — throttle floor, ordering under concurrency, empty-stream finish)
- Consumer pin: `packages/channels-teams/src/adapter.test.ts` streaming paths

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"TeamsMessageStream scheduleFlush queue minIntervalMs","limit":10}'
```

## Verdict
Adopt throttle-plus-serial-queue editing for edit-based streaming on rate-limited channels; adapt interval and finalize-lane semantics. Omit nothing — dropping either mechanism reproduces a distinct stale-text bug.
