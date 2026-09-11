<!-- capsule-v2 -->
# Pending-episode admission gate — when is an episode ready to be summarized exactly once, and which failures skip one item vs abort the batch?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** How do you drive an LLM over a live stream of growing episodes without double-summarizing, summarizing too early, or letting one bad output kill the run?

## TimelineCoordinator pendingEpisodes + summarizePending
**Path/Symbol:** `src/main/timeline-coordinator.ts:TimelineCoordinator.summarizePending` (lines 39-80), `pendingEpisodes` (82-96), `getState` (25-37).
**Signature:** `summarizePending(onStateChange?): Promise<TimelineState>`; private `pendingEpisodes(now = Date.now()): ActivityEpisode[]`.
**Data Shape:** constants `MIN_EPISODE_WINDOW_MS = 8 min`, `ACTIVE_EPISODE_GRACE_MS = 60 s`, `MAX_EPISODES_PER_REQUEST = 8`; state `{items, pendingEpisodeCount, summarizing, lastError?}`.

### Decisive source
```ts
if (this.summarizing) return this.getState();
...
const stored = items.get(episode.id);
if (stored && sameIds(stored.sourceEventIds, episode.events.map((e) => e.id))) return false;
const isNotNewest = index < episodes.length - 1;
const minimumWindowElapsed = now - Date.parse(episode.startTime) >= MIN_EPISODE_WINDOW_MS;
const hasGoneQuiet = now - Date.parse(episode.endTime) >= ACTIVE_EPISODE_GRACE_MS;
const endedAtSleep = ["screen_slept", "session_locked"].includes(episode.events.at(-1)?.kind ?? "");
return minimumWindowElapsed && (isNotNewest || hasGoneQuiet || endedAtSleep);
...
} catch (error) {
  if (!isItemScopedInferenceError(error)) throw error;
  itemError = error;   // skip ONE episode, keep the batch
}
```

**Flow:** single-flight guard returns current state if already running → re-segment from raw store → drop episodes already stored with byte-equal `sourceEventIds` (id equality alone is NOT enough) → admit only episodes ≥8 min old whose end has gone quiet ≥60 s OR that are not the newest OR that ended in sleep/lock → cap at 8 per request → per-item: save then emit state; item-scoped inference failures (`InferenceOutputError` kinds content_filter/incomplete/invalid_output/refusal, or ContentFilter/Length finish-reason/ZodError names — `inference/errors.ts:35-38`) are logged, recorded as public `lastError`, and the loop continues; any other error aborts the whole try block.
**Invariant:** id equality must be paired with sourceEventIds equality for dedup — a regenerated episode with the same id but different membership is treated as changed and re-admitted. `getState` filters stored items through the SAME sameIds check, so stale derived rows vanish from the view even before reconciliation.
**Probe:** `src/main/timeline-coordinator.test.ts` — read directly at pin (suite load BLOCKED by standing no-node_modules `zod`; recorded honestly): :12-54 pins one malformed episode does not block the second summary and surfaces `/couldn't update part of your timeline/i` in `lastError`; :56-99 pins the 8-minute gate boundary (`09:07:59Z` → 0 pending, `09:08:00Z` → 1 pending).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "TimelineCoordinator summarizePending pendingEpisodes", limit: 10 });
```
Executed live byte-for-byte: returns all five `TimelineCoordinator` methods grouped under `timeline-coordinator.ts`, coordinator test helpers below; nothing unrelated ranked above.

## Verdict
Adopt the admission predicate (window + quiet + newest-exception + sleep-terminated exception), the id+membership dedup, and the item-scoped vs batch-aborting error split behind a single-flight flag; adapt constants and error-name lists to your LLM stack; omit Electron-side wiring. Coverage: `no_recorded_issue` on timeline-coordinator.ts and inference/errors.ts; probe is direct-test READ with runner block recorded — not a green run.
