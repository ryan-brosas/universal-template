<!-- capsule-v2 -->
# closeTab Two-Step Teardown — window.close() before Target.closeTarget, serialized

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
Why does every skill's `finally { session.closeTab(...) }` actually work on Chromium forks, and what breaks if a porter "simplifies" it to the CDP call alone?

## Path / Symbol
`skills/cdp/sdk/session.ts` :236-262 (`closeTab` + `closeQueue`); consumers: every data-skill finally block (gmaps :271/:389/:410, gnews :166, rsearch :246, findata :314, ytdl :447, ttdl :452, gsearch :100/:119).

## Signature
```ts
async closeTab(targetId: string, sessionId?: string): Promise<void> {
  const doClose = async () => {
    if (sessionId) {
      try { await this._call('Runtime.evaluate', { expression: 'window.close()' }, { sessionId }); }
      catch { /* session may already be detaching */ }
      await new Promise(r => setTimeout(r, 100));   // let the browser process the close
    }
    try { await this.domains.Target.closeTarget({ targetId }); }
    catch { /* already gone */ }
  };
  this.closeQueue = this.closeQueue.then(doClose, doClose);  // serialize ALL closes
  return this.closeQueue;
}
```

## Data Shape
Fire-and-forget at call sites (`.catch(() => {})`) — cleanup is guaranteed on error paths without blocking snippet return; ordering is guaranteed by the queue, not by awaiting.

## Decisive source
session.ts doc comment :237-250: "`Target.closeTarget` alone succeeds in CDP but **some Chromium forks (Dia, Arc) don't actually close the tab in the browser window** — the tab strip stays out of sync. `window.close()` triggers the browser's own tab-close path, which reliably removes the tab [and] works on tabs opened by script, which includes all tabs created via Target.createTarget." Serialization rationale :251-253: "Without serialization, interleaved closes can kill a session before window.close() takes effect in the browser."

## Flow / Invariant
1. Two steps, always: browser-native close first, CDP teardown second; both best-effort.
2. Serialize closes globally on the Session instance — parallel skills closing tabs concurrently stay safe.
3. Never await closeTab in a hot path; attach `.catch(()=>{})` and move on.

## Probe (direct tests)
SDK suite executed live at this pin: `node --experimental-strip-types --test session.test.ts axview.test.ts video.test.ts` → 17 passed / 0 failed (scratch copy with dev deps; transcript in work record). Live tab lifecycle additionally exercised end-to-end during the MSE probe (createTarget → attach → evaluate → closeTarget) against Chromium/151. Static probe: `grep -c "closeQueue" skills/cdp/sdk/session.ts` → 3.

## Retrieve
`search_graph --project browser-harness-js --query "closeTab"` resolves session.closeTab directly (entry-point surface).

## Verdict
ADOPT verbatim; dropping either step or the serialization reintroduces fork-specific tab leaks that only reproduce on Dia/Arc-style browsers.
