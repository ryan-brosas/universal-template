<!-- capsule-v2 -->
# discord-streaming-history-hygiene

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-discord/src/adapter.ts`
- Symbol: `DiscordAdapter.stream / update / delete / getMessages / fetchHistory / resolveUser`
- Lines: stream :355-393 (handles map :362-376, finally-drain :384-391), getMessages :455-496 (placeholder filter :463-474), fetchHistory :694-743 (thread-starter pull :716-734), resolveUser :633-653 (cache-on-success-only :644-651)
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-discord.src.adapter.DiscordAdapter.fetchHistory`

## Question
When streaming posts multiple real Discord messages plus transient placeholders, how does the adapter keep streamed output, message lifecycle, and reconstructed history self-consistent?

## Signature & Data Shape
```typescript
stream(target, chunks: AsyncIterable<string>): Promise<MessageRef>;   // returns FIRST posted id
getMessages(target): Promise<ThreadMessage[]>;      // read_thread surface, placeholders filtered
fetchHistory(channelId): Promise<DiscordHistoryMessage[]>;          // oldest→newest, best-effort []
resolveUser(userId): Promise<ProviderActor>;        // bare-id fallback on fetch failure
```

## Decisive Source Excerpt
```typescript
// If the source iterable rejects partway, `finish()` must still run so the
// already-posted "_thinking…_" placeholder gets drained to its accumulated
// text instead of being frozen forever; then let the original error propagate.
try {
  for await (const chunk of chunks) { acc += chunk; stream.append(acc); }
} finally {
  await stream.finish();
}
```
History hygiene (:466-474): drop bot-authored messages whose content is exactly one of `STREAM_PLACEHOLDERS` (`_thinking…_` / `_…(continued)_`) — producer text and history filter share ONE exported const so they can't drift. Thread starter rescue (:716-734): a thread's originating message lives in the PARENT channel and is never in the thread's own list — `fetchStarterMessage()` is pulled in and unshifted, best-effort. Cache discipline (:644-651): "Cache ONLY on success — a transient fetch failure must not pin the bare-id fallback forever"; the `{ id, kind:"unknown" }` fallback is returned but deliberately NOT cached.

## Flow
1. Stream opens one handle per posted chunk-message (`handles` Map keyed by id) so edits land on their OWN message; empty streams return a ref with `id: ""`, and `update`/`delete` treat that as a no-op instead of fetching `""`.
2. Reaction refs often arrive as bare `{ id }` with no channel — `channelIdOf(ref) || target.channelId` falls back to the conversation's channel (Slack/Telegram parity).
3. Full per-turn history reconstruction reads Discord as source-of-truth (limit 100, reversed oldest→newest, attachments mapped), so inbound context needs no adapter-side transcript store.
4. Identity context keys tenant by `guildId ?? "direct"` and conversation kind by guild-vs-direct.

## Invariant
Transient stream scaffolding (placeholders, empty-ref sentinels) must be invisible in both the rendered channel and the reconstructed history; failure mid-stream drains what exists rather than freezing placeholders; caches record only verified successes.

## Direct-Test Probe
- File: `packages/channels-discord/src/adapter.test.ts`
- Lines: :87 each posted message edited with ITS own chunk; :134 resolveUser does NOT cache the bare-id fallback; :161 getMessages excludes the bot's own streaming placeholders; :205 addReaction falls back to target channel

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"DiscordAdapter openModal commandPending identityContext fetchHistory","limit":10}'
```

## Verdict
Adopt placeholder-lifecycle hygiene (shared consts, finally-drain, history filtering), thread-starter rescue for parent-hosted context, and cache-on-success-only user resolution. Adapt limits and API shapes per host. Omit nothing — the not-cached-fallback rule prevents permanently poisoned user identity after one transient 5xx.
