<!-- capsule-v2 -->
# Gap/duration/boundary segmentation — how do timestamp-ordered events become task episodes without splitting live work or spanning private intervals?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** Where are the exact episode cut points, and which event ends up in which episode when a boundary fires?

## Segmenter flush ladder
**Path/Symbol:** `src/main/episode-segmenter.ts:segmentActivityEvents` (lines 23-82).
**Signature:** `segmentActivityEvents(input: ActivityEvent[], options?: SegmentOptions): ActivityEpisode[]`.
**Data Shape:** unsorted filtered events in; defaults idle 5 min, max span 13 min, context-switch quiet 2 min, context lead 30 s; out: ordered episodes of event arrays (never empty episodes).

### Decisive source
```ts
if (event.kind === "privacy_boundary") {
  flush();
  continue;
}
...
const shouldStartNew = Boolean(
  previous && startedAt && (
    eventTime - Date.parse(previous.timestamp) >= idleGapMs ||
    eventTime - Date.parse(startedAt.timestamp) >= maxDurationMs ||
    previous.kind === "screen_slept" || previous.kind === "session_locked" ||
    event.kind === "screen_woke" || event.kind === "session_unlocked" ||
    Boolean(lastWork && eventTime - Date.parse(lastWork.timestamp) >= contextSwitchGapMs &&
      signalsTaskContextSwitch(current, lastWork, event))
  )
);
if (shouldStartNew) flush();
current.push(event);
if (event.kind === "screen_slept" || event.kind === "session_locked") flush();
```

**Flow:** re-filter protected + drop collector self-events + sort by parsed timestamp → single pass accumulating `current` → cut on idle/max/sleep-latch/wake/context-switch → sleep/lock append THEN flush (terminator belongs to closing episode); wake/unlock flush BEFORE append (opener belongs to new episode); `privacy_boundary` sentinels cut without entering any episode; final flush drains.
**Invariant:** every emitted episode contains at least one work-evidence kind (`isWorkEvent`); a boundary event is never silently dropped mid-episode — it always terminates one.
**Probe:** `src/main/episode-segmenter.test.ts` — executed GREEN at pin ("tests 31, pass 30" combined run): 12.99-min span stays 1 episode, 13-min splits to 2; screen sleep/wake yields 2 episodes with Editor before, Browser after; lock/unlock test pins `episodes[0].events.at(-1).kind === "session_locked"` and `episodes[1].events[0].kind === "session_unlocked"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "episode segment timeline project events", limit: 10 });
```
Executed live: `segmentActivityEvents` returns rank #1 (`src/main/episode-segmenter.ts` lines 23-82), ahead of `prepareEpisodeEvents`, `compactAdjacentContextEvents`, and projection callers.

## Verdict
Adopt the ordered cut ladder and the append-then-flush vs flush-then-append asymmetry for sleep/wake terminators; adapt the default minute constants and the `isWorkEvent` kind list to your domain's evidence kinds; omit the macOS collector self-exclusion (`isCollectorHostEvent`) unless your host observes itself too. Coverage: `no_recorded_issue` on `src/main/episode-segmenter.ts`; suite executed green at pin.
