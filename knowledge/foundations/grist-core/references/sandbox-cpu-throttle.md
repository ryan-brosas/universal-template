<!-- capsule-v2 -->
# Sandbox CPU throttle — how do you cap an untrusted process's CPU without cgroups?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Using only signals and /proc sampling, how do you hold a runaway sandbox to a target CPU fraction while leaving bursty short work untouched?

## SIGSTOP/SIGCONT duty cycle driven by pidusage ctime averaging
**Path/Symbol:** `app/server/lib/Throttle.ts:Throttle` (whole file, 321L): `_update` (163–242), `_updateThrottle` (247–257), `_throttle` duty cycle (286–291), `_letProcessRun` (262–280), `ThrottleTiming` defaults (51–60).
**Signature:** `constructor({ pid, readPid?, tracedPid?, logMeta, timing? })`; `stop()`; test hook `get testStats`.
**Data Shape:** `defaultThrottleTiming = { dutyCyclePositiveMs: 50, samplePeriodMs: 1000, targetAveragingPeriodMs: 20000, minimumAveragingPeriodMs: 6000, minimumLogPeriodMs: 10000, targetRate: 0.25, maxThrottle: 10, traceNudgeOffset: 5 }`; samples `{ time, cpuDuration (OS ctime), offDuration }`; anchor/nextAnchor for averaging.

### Decisive source
```ts
// average cpu use per second since the anchor:
const rate = (current.cpuDuration - this._anchor.cpuDuration) / dt;
if (rate <= targetRate) { this._updateThrottle(0); return; }
const on = dt - off;                     // time actually unpaused in the window
if (on <= 0) { return; }
const rateWithoutThrottling = (current.cpuDuration - this._anchor.cpuDuration) / on;
//   one duty cycle lasts: quantum * (1 + throttleFactor)
//   cpu per second is: rateWithoutThrottling / (1 + throttleFactor)
//   so: throttleFactor = (rateWithoutThrottling / targetRate) - 1
const throttleFactor = rateWithoutThrottling / targetRate - 1;
this._updateThrottle(Math.min(throttleFactor, this._timing.maxThrottle));
...
private _throttle(on: boolean) {
  this._letProcessRun(on);               // SIGCONT / SIGSTOP
  const dt = this._timing.dutyCyclePositiveMs * (on ? 1.0 : this._throttleFactor);
  if (!on) { this._offDuration += dt; }
  this._dutyCycleTimeout = setTimeout(() => this._throttle(!on), dt);
}
```

**Flow:** sample the process's cumulative CPU (`pidusage().ctime`) every second → maintain a rolling anchor ~20s back (replaced via `nextAnchor` so the window slides) → below target or under the 6s minimum-observation floor ⇒ no throttling → above ⇒ compute the pause/run ratio that projects observed unthrottled rate down to target, capped at 10× positive-phase length → run a SIGSTOP/SIGCONT duty cycle (50ms run windows separated by factor-scaled pauses), accumulating `offDuration` which feeds back into the `on`-time correction so throttling doesn't overshoot. A gvisor/ptrace wrinkle: also STOP the traced child plus one delayed "nudge" STOP, because signal delivery under ptrace is unreliable. `stop()` always leaves the process RUNNING.
**Invariant:** never throttle before enough samples exist (min averaging period) — startup bursts are exempt by design; the process must NEVER be left stopped (every exit path clears the duty-cycle timeout and sends SIGCONT); measurement races with `stop()` are guarded by re-checking `_stopped` after the async read; low target rates may be mathematically unobtainable under the maxThrottle cap — accepted and logged, not crashed.
**Probe:** `test/server/lib/Throttle.ts` — drives fake pidusage samples and asserts duty-cycle behavior incl. stop-leaves-running and anchor-window math.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "Throttle _update throttleFactor dutyCycle", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt when you host untrusted compute in-process trees without container limits (local dev sandboxes, plugin runners): ctime sampling + projected duty cycling is portable pure-userspace CPU governance. Adapt sample period, target rate, caps, and the traced-pid nudge (only needed for gvisor-style tracers). Omit entirely where cgroups/JobObjects are available — kernel enforcement beats signals.
