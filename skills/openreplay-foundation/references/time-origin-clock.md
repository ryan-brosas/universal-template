<!-- capsule-v2 -->
# Time-origin clock discipline — how do you build session timestamps from a monotonic clock that still agree with the server's wall clock?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** Why does the tracker compute `Date.now() - performance.now()` at start and re-anchor it on every session transition instead of just using Date.now()?

## utils.ts now / adjustTimeOrigin / getTimeOrigin
**Path/Symbol:** `tracker/tracker/src/main/utils.ts:adjustTimeOrigin` (:13-15), `now` (:22-25), module state `timeOrigin` (:11).
**Signature:** `export function adjustTimeOrigin(): void`; `export const now: () => number`.
**Data Shape:** Module-level `timeOrigin` (ms epoch); `App.delay` (server-vs-client skew from token, applied in `App.timestamp(): number { return now() + this.delay }`); consumed by every Timestamp message and by `coldStartTs`/`bufferDiff` math.

### Decisive source
```ts
// Buggy to use `performance.timeOrigin || performance.timing.navigationStart`
// https://github.com/mdn/content/issues/4713
// Maybe move to timer/ticker
let timeOrigin: number = IN_BROWSER ? Date.now() - performance.now() : 0
export function adjustTimeOrigin() {
  timeOrigin = Date.now() - performance.now()
}

export const now: () => number =
  IN_BROWSER && !!performance.now
    ? () => Math.round(performance.now() + timeOrigin)
    : () => Date.now()
```

**Flow:** at module load AND before every session transition (`_start` when not cold-start, coldStart cycle, offlineRecording), `adjustTimeOrigin()` re-anchors the epoch offset → all message timestamps come from `performance.now() + timeOrigin`, which is MONOTONIC within a session (immune to user clock changes mid-session) but EPOCH-anchored so the player can render wall-clock-aligned frames → the server computes `Delay = serverMs - clientTs` at start, signs it into the token, and the tracker adds it in `App.timestamp()` → offline mode deliberately skips delay correction (`IsOffline → device timestamp wins`) because a gap invalidates the skew estimate.
**Invariant:** Never mix raw Date.now() into per-event timestamps: wall-clock jumps (NTP syncs, manual changes) would reorder events inside a replay; performance.now() cannot go backwards. Re-anchoring at each START (not once per page) keeps each SESSION's origin honest after background throttling, while the ≤5-min bufferDiff credit (server side) prevents pre-session buffering from shifting the recorded start time. The comment is load-bearing history: `performance.timeOrigin` itself is known-buggy cross-browser — derive the anchor arithmetically.
**Probe:** `grep -n 'timeOrigin = Date.now() - performance.now()' tracker/tracker/src/main/utils.ts` from repo root → line 14; `grep -n 'performance.now() + timeOrigin' tracker/tracker/src/main/utils.ts` → line 23 (verified live). Direct tests: `npx jest tests/utils.test.ts` in `tracker/tracker` → 44/44 green (suite covers utils plane incl. stars/normSpaces neighbors).
**Retrieve:** search_graph project openreplay query "adjustTimeOrigin timeOrigin now" → resolves Function nodes in main/utils.ts (Module/File nodes carry tokens here; if BM25 misses use `search_code --pattern 'adjustTimeOrigin' --file-pattern '*.ts'`).

## Verdict
Adopt arithmetic epoch-anchoring of a monotonic clock with per-session re-anchor + signed server-delay correction as pure time behavior; adapt to your platform clock APIs; omit the IN_BROWSER fallback branch if you are browser-only.
