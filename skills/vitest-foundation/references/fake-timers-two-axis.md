<!-- capsule-v2 -->
# FakeTimers two-axis clock wrapper — how do Date-only mocking and full timer faking coexist without losing the mocked date?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b35847`); Codebase Memory `vitest`. **Question:** How do you layer `vi.setSystemTime` (Date-only) and `vi.useFakeTimers` (all timers) over one @sinonjs/fake-timers clock, and which timers must never be faked in a worker pool?

## `FakeTimers` state machine
**Path/Symbol:** `packages/vitest/src/integrations/mock/timers.ts:FakeTimers` (whole class, 19–268); consumed by `integrations/vi.ts`.
**Signature:** `constructor({global, config}: {global: typeof globalThis; config: FakeTimersConfig})`; methods `useFakeTimers/useRealTimers/setSystemTime/getMockedSystemTime/reset/advanceTimersByTime[Async]/advanceTimersToNextTimer[Async]/runAllTimers[Async]/runOnlyPendingTimers[Async]/clearAllTimers/getTimerCount/configure/isFakeTimers/setTimerTickMode`.
**Data Shape:** two booleans/fields — `_fakingTime` (full clock installed) and `_fakingDate` (Date/Temporal-only clock) with the documented truth table: `(false,null)` initial → `(false,date)` setSystemTime first → `(true,null)` useFakeTimers first → `(true,date)` UNREACHABLE. `RealDate = globalThis.Date` captured at module load so real time survives faking.

### Decisive source
```ts
useFakeTimers(): void {
  const fakeDate = this._fakingDate || Date.now()      // carry forward mocked date
  if (this._fakingDate) { this._clock.uninstall(); this._fakingDate = null }
  if (this._fakingTime) this._clock.uninstall()        // re-install picks up new config

  let toFake = this._userConfig?.toFake
  if (isChildProcess() && toFake?.includes('nextTick')) {
    throw new Error('process.nextTick cannot be mocked inside child_process')
  }
  let toNotFake = this._userConfig?.toNotFake
  if (toFake === undefined && toNotFake === undefined) {
    // Do not mock timers internally used by node by default.
    toFake = (Object.keys(this._fakeTimers.timers) as FakeMethod[])
      .filter(timer => timer !== 'nextTick' && timer !== 'queueMicrotask')
  }
  if (isChildProcess() && toNotFake && !toNotFake.includes('nextTick'))
    toNotFake = [...toNotFake, 'nextTick']

  this._clock = this._fakeTimers.install({
    now: fakeDate, ...this._userConfig,
    ...(toFake && { toFake }), ...(toNotFake && { toNotFake }),
    ignoreMissingTimers: true,
  })
  this._fakingTime = true
}

setSystemTime(now?: string | number | Date): void {
  const date = (typeof now === 'undefined' || now instanceof Date) ? now : new Date(now)
  if (this._fakingTime) { this._clock.setSystemTime(date); return }   // cheap on full clock
  const newFakingDate = date ?? new Date(this.getRealSystemTime())
  if (this._fakingDate) { this._fakingDate = newFakingDate; this._clock.setSystemTime(newFakingDate) }
  else {                                                              // lightweight Date-only clock
    this._fakingDate = newFakingDate
    this._clock = this._fakeTimers.install({ now: newFakingDate, toFake: ['Date', 'Temporal'], ignoreMissingTimers: true })
  }
}

reset(): void {
  if (this._checkFakeTimers()) {
    const { now } = this._clock
    this._clock.reset()             // clears pending timers...
    this._clock.setSystemTime(now)  // ...but KEEPS the faked wall-clock
  }
}

private _checkFakeTimers() {
  if (!this._fakingTime)
    throw new Error('A function to advance timers was called but the timers APIs are not mocked. Call `vi.useFakeTimers()` in the test file first.')
  return this._fakingTime
}
```

**Flow:** `setSystemTime` before any faking installs a minimal clock faking ONLY `['Date','Temporal']`; a later `useFakeTimers` uninstalls it and re-installs the full clock seeded at the previously mocked instant (`_fakingDate || Date.now()`), so user-visible time never jumps backwards. Default `toFake` excludes `nextTick`+`queueMicrotask` (node internals rely on them; worker RPC would deadlock); child_process pools hard-refuse or force-exclude `nextTick`. Advance APIs (`tick`, `next`, `runAll`, …) all funnel through `_checkFakeTimers()` which fails loud, not silently. `advanceTimersToNextTimer` does `clock.next()` then `clock.tick(0)` because sinon's `next()` advances but doesn't fire same-instant timers (sinonjs/fake-timers#250), stopping early when `countTimers()===0`.
**Invariant:** (1) at most ONE clock installed at a time; installing always goes through uninstall-first; (2) the mocked DATE survives promotion from Date-only to full faking; (3) `reset()` = drop pending timers, keep wall-clock; `dispose()`/`useRealTimers()` restores both axes; (4) microtask machinery is never faked by default — only via explicit user config; (5) advancing without faking throws an actionable error instead of no-op.

**Probe:** shared Jest-derived battery `test/unit/test/fixtures/timers.suite.ts` imports the class DIRECTLY from `packages/vitest/src/integrations/mock/timers` and runs under node (`timers-node.test.ts`) and jsdom (`timers-jsdom.test.ts`); `date-mock.test.ts`, `timers-getMockedSystemTime.test.ts`, `timers-queueMicrotask.test.ts`, `timers-temporal.test.ts` pin the axis behaviors. Caveat: suite needs installed deps; source read byte-for-byte at pinned HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "timers run getWorkerState resolveTestRunner", limit: 8 });
// observed cluster 0 members incl. FakeTimers.runOnlyPendingTimers (integrations/mock/timers.ts 72-82)
// alongside vi.runOnlyPendingTimers wrappers (integrations/vi.ts 536-544).
```

## Verdict
Adopt the two-axis model + promotion-preserves-date + default-toFake denylist for any harness that fakes time inside pooled workers. Adapt the excluded-timer list to your transport (e.g. MessageChannel-based pools may need more exclusions). Omit Temporal if absent in host runtimes; keep the module-load `RealDate` capture trick.
