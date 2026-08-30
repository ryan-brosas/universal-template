<!-- capsule-v2 -->
# scroll-drain background-work gate — how do background intervals avoid fighting the UI for the event loop?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** A TUI runs polling intervals (stats, dev bar, notifications) alongside user scrolling — what coordination primitive keeps background work from janking scroll frames without a scheduler rewrite?

## markScrollActivity / waitForScrollIdle: module-scope debounce flag + cooperative await
**Path/Symbol:** `src/bootstrap/state.ts`:`scrollDraining`/`scrollDrainTimer`/`SCROLL_DRAIN_IDLE_MS` (`:792-794`), `markScrollActivity` (`:798-806`), `getIsScrollDraining` (`:811-813`), `waitForScrollIdle` (`:818-824`). Sibling pattern: deferred interaction clock (`interactionTimeDirty`, `updateLastInteractionTime(immediate?)`, `flushInteractionTime`, `:665-689`) — batch many keypresses into ONE Date.now() per Ink render frame.
**Signature:** `markScrollActivity(): void`; `getIsScrollDraining(): boolean`; `await waitForScrollIdle(): Promise<void>`; `updateLastInteractionTime(immediate?: boolean): void`; `flushInteractionTime(): void`.
**Data Shape:** `scrollDraining: boolean` + self-clearing timer, idle window `SCROLL_DRAIN_IDLE_MS = 150` (line-pinned :794). Module-scope on purpose — comment (:790-791): "ephemeral hot-path flag, no test-reset needed since the debounce timer self-clears".

### Decisive source
```ts
export function markScrollActivity(): void {
  scrollDraining = true
  if (scrollDrainTimer) clearTimeout(scrollDrainTimer)
  scrollDrainTimer = setTimeout(() => {
    scrollDraining = false
    scrollDrainTimer = undefined
  }, SCROLL_DRAIN_IDLE_MS)
  scrollDrainTimer.unref?.()          // never holds the process open
}
// :815-824
/** Await this before expensive one-shot work (network, subprocess) that could
 *  coincide with scroll. Resolves immediately if not scrolling; otherwise
 *  polls at the idle interval until the flag clears. */
export async function waitForScrollIdle(): Promise<void> {
  while (scrollDraining) {
    // bootstrap-isolation forbids importing sleep() from src/utils/
    // eslint-disable-next-line no-restricted-syntax
    await new Promise(r => setTimeout(r, SCROLL_DRAIN_IDLE_MS).unref?.())
  }
}
```

**Flow:** ScrollBox scrollBy/scrollTo calls `markScrollActivity()` per event → flag true for 150ms after the LAST event (each event resets the timer) → background intervals check `getIsScrollDraining()` and early-return (work resumes next tick after settle) → one-shot expensive work (network/subprocess kickoff) `await`s `waitForScrollIdle()` before starting.
**Invariant:** Two consumers with different contracts: interval loops POLL the boolean and skip a tick; blocking-ish one-shots AWAIT the promise which polls at the same 150ms cadence until clear. The timer is `.unref()`'d twice (arm timer + poll sleep) so neither scroll nor waiting can keep a headless process alive. The flag lives at MODULE scope, not in STATE — deliberately outside resetStateForTests because it is transient UI-coordination, not session data. The sibling deferred-clock pattern batches timestamp reads per render frame but requires `immediate=true` from post-render callbacks (useEffect), else the timestamp goes stale while the user sits in a permission dialog.
**Probe:** Deterministic pins: `grep -n 'SCROLL_DRAIN_IDLE_MS = ' src/bootstrap/state.ts` → `794:` (=150); `grep -n 'forbids importing sleep' src/bootstrap/state.ts` → `820:`; `grep -n 'unref' src/bootstrap/state.ts | wc -l` → `3` (:805 arm, :822 poll, plus none other — verify count before writing).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "scroll draining waitForScrollIdle markScrollActivity", limit: 10 });
```

## Verdict
Adopt the debounce-flag gate for any single-threaded UI host running background polls — it's ~30 lines total. Adapt the idle window to your frame budget and wire your scroll primitive to the marker. Omit the immediate-mode variant of the interaction clock if you don't render-batch timestamps.
