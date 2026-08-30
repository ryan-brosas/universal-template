<!-- capsule-v2 -->
# Cross-process floor arbitration — how do several editor processes agree on exactly one microphone owner using only a shared directory?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the file-based mutual-exclusion protocol (claim, heartbeat, staleness, preemption) for a singleton hardware resource?

## Floor arbiter
**Path/Symbol:** `src/live/queue.ts:class LiveFloorArbiter` (:166-388); constants `LIVE_QUEUE_TICK_MS=1_000`, `LIVE_QUEUE_STALE_MS=8_000` (:31-32).
**Signature:** `join()/leave()/tick()/setFocused(focused)/get hasFloor()` with callbacks `{onActivated(cause), onDeactivated()}`.
**Data Shape:** Per-member JSON heartbeat files in `<agentDir>/live-queue/members/<sanitized-id>.json`; one shared `floor.json` claim `{holderId, pid, token, claimedAt}`.

### Decisive source
```ts
#evaluate(): void {
  const aliveMembers = this.#readMembers().filter((m) => this.#isMemberAlive(m));
  const claim = this.#readClaim();
  const holderAlive = claim !== undefined &&
    (claim.pid === this.#pid || this.#isProcessAlive(claim.pid)) &&
    aliveMembers.some((m) => m.id === claim.holderId && now - m.heartbeatAt <= LIVE_QUEUE_STALE_MS);

  if (this.#hasFloor) {
    if (!this.#joined || claim?.token !== this.#token || claim.holderId !== this.#id) {
      this.#hasFloor = false;
      this.#callbacks.onDeactivated();          // displaced holder steps down NEXT tick
    }
    return;
  }
  if (claim && holderAlive) {
    // Only a genuinely focused challenger preempts...
    if (this.#policy === "focus" && this.#focused === true && claim.holderId !== this.#id)
      this.#claim("focus", true);               // atomic REPLACE
    return;
  }
  if (claim && !holderAlive) rmSync(this.#floorFile, { force: true });  // crashed holder
  if (this.#policy === "fifo") {
    if (aliveMembers[0]?.id === this.#id) this.#claim("fifo", false);
    return;
  }
  if (this.#focused !== false)                  // vacant floor needs only NOT-unfocused
    this.#claim(this.#focused === true ? "focus" : "background", false);
}
```
Claim primitives (`#claim`, :352-377): non-preempt uses `openSync(floorFile,"wx")` exclusive-create; preempt uses atomic temp+rename write; EITHER WAY the winner re-reads and activates ONLY if the confirmed token equals its own random per-instance token. Liveness (`defaultIsProcessAlive` :86-98): `process.kill(pid,0)` true; ESRCH→dead; **EPERM→alive-but-unowned**. Sweep (`#sweep` :295-310) deletes members whose pid is dead or heartbeat older than 8s (own pid exempt). Writes are temp-file+`renameSync` atomic (:160-164).

**Flow:** join writes member file → tick loop (1s): rewrite heartbeat → sweep dead members → evaluate claim → activate/deactivate via confirmed-token check.
**Invariant:** Exactly one process holds the floor because ownership requires reading back YOUR OWN random token; focus asymmetry is deliberate — gaining focus grants claiming/preemption rights, LOSING focus never yields (a conversation survives alt-tab); a merely-vacant floor needs only "not known unfocused" so terminals without initial focus state still work.
**Probe:** `tests/live-queue.test.ts` (:72 vacant-floor unknown-focus claim, :81 fifo oldest-member, :100 focused-challenger-preempts + holder-steps-down-next-tick, :123 losing-focus-never-yields, :134 crashed-holder reclaim, :163 stale-heartbeat sweep).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "LiveFloorArbiter evaluate claim floor.json", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole protocol: wx-exclusive first-claim, rename-replace preemption, read-back-token confirmation, pid+heartbeat dual liveness (EPERM=alive), asymmetric focus policy. Adapt directory location and tick/stale budgets. Omit the pi session-id label formatting.
