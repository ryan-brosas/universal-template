<!-- capsule-v2 -->
# chunked-stream-frozen-boundaries

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-discord/src/chunked-message-stream.ts`
- Symbol: `ChunkedMessageStream` / `refreezeBoundaries` / `clampToHardLimit`
- Lines: whole file 256L; refreezeBoundaries :190-214, clampToHardLimit :36-45, findUnpairedFenceStart :51-57, setup-error latch :107-148
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-discord.src.chunked-message-stream.ChunkedMessageStream.refreezeBoundaries`

## Question
How do you split an unboundedly-growing agent reply across N hard-limited channel messages (Discord: 2000 chars each) when already-posted chunks can never shrink or reflow?

## Signature & Data Shape
```typescript
new ChunkedMessageStream({
  limit?: number,                                  // soft limit, default 1900 (NOT the 2000 hard limit)
  minIntervalMs?: number,
  postPlaceholder: (text) => Promise<string>,      // mints a Discord message, returns id
  updateAt: (id, text) => Promise<void>,
  transform?: (text) => string,                    // per-chunk markdown translation
}).append(fullTextSoFar); finish();
```
State: `buffer` (full accumulated text), `boundaries: number[]` (sorted frozen end offsets), `streams: MessageStream[]` (one per posted message), `setupPromise` + `setupError`.

## Decisive Source Excerpt
```typescript
private refreezeBoundaries(): void {
  let lastFrozen = this.boundaries.at(-1) ?? 0;
  while (this.buffer.length - lastFrozen > this.limit) {
    const window = this.buffer.slice(lastFrozen, lastFrozen + this.limit);
    let breakAt = window.lastIndexOf("\n");
    if (breakAt < this.limit / 4) breakAt = window.lastIndexOf(" ");
    if (breakAt < 0) breakAt = this.limit - 1;
    let candidate = lastFrozen + breakAt + 1;
    // Block-keeps-whole: move boundary back if it lands inside an open fence —
    // only if the fence opener sits in the latter ~70% of the active chunk.
    const fenceStart = findUnpairedFenceStart(this.buffer, candidate);
    if (fenceStart !== null && fenceStart > lastFrozen + Math.floor(this.limit * 0.3)) {
      candidate = fenceStart;                      // whole block moves to the NEXT message
    }
    this.boundaries.push(candidate);               // FROZEN — never recomputed or moved
    lastFrozen = candidate;
  }
}
```
And the headroom rule (`DEFAULT_LIMIT = 1900`, DISCORD_HARD_LIMIT = 2000): "a chunk sliced to exactly 2000 raw chars would exceed 2000 once transformed and Discord would reject the edit with BASE_TYPE_MAX_LENGTH." The final safety net `clampToHardLimit` re-appends a `\n``` closer when truncation severs an open fence (odd triple-backtick count).

## Flow
1. Every `append(fullText)` replaces the buffer view and refreezes boundaries greedily forward from the last frozen one; boundaries accumulate but never move.
2. `ensureStreamsAndDispatch` lazily posts one placeholder per required chunk (`_thinking…_` first / `_…(continued)_` for continuations — exported as `STREAM_PLACEHOLDERS` so adapter history filtering can never drift from producer text), then dispatches slice `[start,end)` of the CURRENT buffer to each chunk's stream.
3. Continuation chunks get their context re-opened: `detectOpenContext(buffer.slice(0,start))` → `renderContextOpener(ctx)` prepends e.g. ```` ```python\n ```` so message N+1 doesn't start with raw code rendered as plain text; the matching closer is added by the per-chunk transform (`autoCloseOpenMarkdown`).
4. New-chunk creation is serialised through a promise chain; a rejecting `postPlaceholder` is recorded ONCE in `setupError` (the chain itself stays rejection-free via `.catch`) and rethrown deterministically at the next `append`/`finish`.
5. Adapter-side, `stream()` keeps a `handles` Map keyed by posted-message id so `updateAt(id,…)` edits the message that OWNS that id — multi-chunk replies must not edit message #0 forever — and drains placeholders in `finally` even when the source iterable rejects.

## Invariant
Once posted, a chunk's boundary offset is immutable (posted text never shrinks); every transformed edit stays ≤ the platform hard limit because the SOFT limit reserves transform headroom and the clamp guarantees the ceiling; concatenated slices reproduce the full buffer with no lost characters.

## Direct-Test Probe
- File: `packages/channels-discord/src/chunked-message-stream.test.ts`
- Lines: :58 frozen boundaries don't move; :137 block-keeps-whole; :170 fallback re-opener path; :257 no transformed chunk exceeds 2000 even with open fence; :292 soft-limit headroom proof; :325/:358 rejecting postPlaceholder surfaces without unhandled rejection
- Also `adapter.test.ts` :87 "stream() edits each posted message with ITS own chunk, not all-on-first"

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"ChunkedMessageStream refreezeBoundaries clampToHardLimit","limit":10}'
```
(Twin family: `channels-slack/src/chunked-message-stream.ts`, telegram `chunked-edit-stream.ts`.)

## Verdict
Adopt frozen-boundary greedy chunking with soft-limit-below-hard-limit headroom, block-keeps-whole fence rescue, and the single-recorded-setup-error latch. Adapt break heuristics and limit constants per host. Omit nothing — the 1900≠2000 gap IS the porting trap.
