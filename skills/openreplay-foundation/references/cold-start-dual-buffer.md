<!-- capsule-v2 -->
# Cold-start dual-buffer buffering — how do you record before consent and replay the buffer when (and only when) start() arrives?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What is the state machine that captures DOM events for a 30-second activation window without starting a session, then flushes it losslessly into the real session?

## App.coldStart / _cStartCommit / _nCommit
**Path/Symbol:** `tracker/tracker/src/main/app/index.ts:coldStart` (:1237-1281), `_cStartCommit` (:1017-1025), `_nCommit` (:947-1007), `bufferedMessages1/2`, `coldInterval`.
**Signature:** `public async coldStart(startOpts: StartOptions = {}, conditional?: boolean)`; private `_cStartCommit(): void`.
**Data Shape:** Two rotating buffers `bufferedMessages1`/`bufferedMessages2`; `activityState = ActivityState.ColdStart | Starting | Active`; `coldInterval` 30 s; `coldStartTs` anchors the pre-session timeline; `coldStartCommitN` mod-2 counter.

### Decisive source
```ts
this.coldInterval = setInterval(() => { cycle() }, 30 * second)
// cycle(): stop(false) → activityState = ColdStart → observe() → ticker.start()
private _cStartCommit(): void {
    this.coldStartCommitN += 1
    if (this.coldStartCommitN === 2) {          // every 2nd tick (~60ms) ...
      const payload = [Timestamp(this.timestamp()), TabData(this.session.getTabId())]
      this.bufferedMessages1.push(...payload)
      this.bufferedMessages2.push(...payload)
      this.coldStartCommitN = 0
    }
}
```

**Flow:** coldStart runs `cycle()` immediately + every 30 s → each cycle STOPS the old capture, flips to ColdStart, re-observes the DOM, restarts the ticker, and alternately RESETS buffer1 or buffer2 (even cycles reset buffer1, odd reset buffer2) so exactly one buffer always holds the last ≤30 s of events → on real `_start()`, the surviving buffer's messages are posted to the worker BEFORE live traffic, prefixed with Timestamp+TabData → normal-mode `_nCommit` unshifts Timestamp+TabData per ~30 ms tick and posts via requestIdleCb.
**Invariant:** The dual buffer is a loss-tolerance tradeoff, not duplication: one is always being reset while the other accumulates, guaranteeing at most 30 s of pre-consent context and never sending stale frames. Cold-start batches commit every SECOND tick (~60 ms) deliberately — fewer, larger batches avoid "1000 batches" hammering BatchWriter during page load. Keepalive path in `_nCommit`: after 1000 empty ticks (~30 s), send a Timestamp+TabData-only batch so the backend session stays alive with zero user activity. `checkSessionToken()` gates resume-vs-new by comparing a stored protocol version string ("2") against the current PROTO_VERSION — a version mismatch forces newSessionID even with a valid token.
**Probe:** `grep -n 'emptyBatchCounter < 1000' tracker/tracker/src/main/app/index.ts` from repo root → line 974; `grep -n '30 \* second' tracker/tracker/src/main/app/index.ts` → line 1279 (verified live). Direct tests: cold-start seams are exercised via main.test.ts + observer suites; the keepalive counter arithmetic is pinned here by grep anchor (no dedicated suite).
**Retrieve:** search_graph project openreplay query "coldStart bufferedMessages ColdStart activityState" → rank-1 Methods `API.coldStart :397-406`, `App.coldStart :1237-1281` line-exact.

## Verdict
Adopt rotate-and-hold dual buffering with commit-throttling and empty-tick keepalives as pure pre-activation recording behavior; adapt the 30 s window and ConditionsManager trigger plumbing to your consent model; omit the analytics-token conditional-fetch variant if you don't gate flags behind a doNotRecord round-trip.
