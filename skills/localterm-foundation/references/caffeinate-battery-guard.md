<!-- capsule-v2 -->
# Caffeinate battery guard — when may the daemon refuse to hold a power assertion the mode asked for?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I enforce a battery floor over an on/automatic keep-awake without ever wedging keep-awake off on bad data, and how do I schedule the unavoidable polling?

## Suppression latch + adaptive poll scheduler
**Path/Symbol:** `packages/server/src/caffeinate-battery-guard.ts:CaffeinateBatteryGuard.shouldActivate` (57–74), `.performBatteryCheck` (124–149), `.computeBatteryDelay` (174–198).
**Signature:** `shouldActivate(wantActive: boolean): boolean`; `runBatteryCheck(): Promise<void>`; private `scheduleBatteryCheck(status: BatteryStatus | null)`.
**Data Shape:** `batteryLow` cached suppression flag; `lastBatteryStatus: BatteryStatus|null` (null = never read OR failed read); `hasProbedBattery` separate first-probe latch; `batteryCheckInFlight` promise coalescer.

### Decisive source
```ts
// :143-148 — fail-open is the load-bearing polarity
const nextLow = status !== null && status.isOnBattery && status.percent <= threshold;
if (nextLow !== this.batteryLow) { this.batteryLow = nextLow; this.emitChange(); }
this.recompute();
```

**Flow:** every activation decision funnels through `shouldActivate(wantActive)` → suppression = `guardApplies && (batteryLow || needsFirstProbe)` where guard applies only when supported ∧ threshold ≠ null → arming while wantActive∧applies schedules the adaptive check; disarming clears the timer. Probe happens ONLY while a mode wants active (`performBatteryCheck` early-returns otherwise — idle/off automatic never reads the battery). First arm fires immediately (`!hasProbedBattery` ⇒ no MAX wait — regression-tested: a freshly booted low-battery machine must not briefly hold the assertion). Delay ladder in `computeBatteryDelay`: threshold null → MAX; already suppressed → MIN (resume fast when plugged in); null status / not-on-battery / null minutesToEmpty → MAX; else `(minutesToEmpty·60000 · (percent−threshold)/percent) / 2`, clamped [5s, 15min] (TIME_FRACTION=2 halves the interpolated time-to-threshold as EWMA-lag buffer). Failed reads stay armed at MAX — "retries instead of going silent" is itself regression-tested with fake timers.
**Invariant:** fail-open on bad data — a missing battery or transient pmset error can NEVER take keep-awake from the user; only a successful read proving `isOnBattery && percent <= floor` suppresses. Keep `hasProbedBattery` SEPARATE from `lastBatteryStatus !== null`: booting below the floor must suppress before the first probe resolves, while a later failed read (status→null) must still fail open rather than re-gating forever.
**Probe:** `packages/server/tests/caffeinate-manager.test.ts::"suppresses on the first probe without waiting for the adaptive timer"` (:503), `"fails open when the probe returns null"` (:533), `"retries on the MAX interval after a failing probe instead of going silent"` (:542 — fake-timer probe-count assertions), `"does not run the probe while the mode does not want active"` (:580).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "shouldActivate battery", limit: 8, fields: ["signature", "name", "file"] });
// → CaffeinateBatteryGuard.shouldActivate @ caffeinate-battery-guard.ts:57-74 (+ performBatteryCheck/scheduleBatteryCheck)
await mcp.codebase_memory.search_graph({ project: "localterm", query: "thresholdChanged", limit: 3 });
```

## Verdict
Adopt the shouldActivate funnel + two-latch design + adaptive delay formula verbatim; adapt constants (MIN/MAX/TIME_FRACTION) to host discharge rates; omit the pmset/sysfs probe bodies if the host exposes its own battery API (inject a BatteryProbe). All four decisive tests live at this commit; coverage clean.
