<!-- capsule-v2 -->
# App start-deferral gate — how do you make session `start()` idempotent, election-aware, and deferred until the tab is visible?

**Source:** OpenReplay AGPL-3.0 (tracker MIT) `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What stands between a user calling `start()` and the admission request actually firing?

## Public start() → signalIframeTracker → waitStart latch → _start
**Path/Symbol:** `tracker/tracker/src/main/app/index.ts` — `start` (:1821–1852), `waitStart` (:1789–1798), `allowAppStart` (:748–754), `canStart` latch (:272), `signalIframeTracker` (:695–745).
**Signature:** `async start(...args: Parameters<App['_start']>): Promise<StartPromiseReturn>`; `allowAppStart(): void` sets `canStart = true` and clears the 250 ms fallback timer.
**Data Shape:** `ActivityState = {NotActive, Starting, Active, ColdStart}`; boolean latch `canStart`; iframe retry loop state `{maxRetries:10, retries, delay:250→*1.5, cumulativeDelay, stopAttempts}`.

### Decisive source
```ts
async start(...args) {
  if (this.activityState === ActivityState.Active ||
      this.activityState === ActivityState.Starting)
    return Promise.resolve(UnsuccessfulStart('...started already.'))   // idempotence gate
  if (this.insideIframe) this.signalIframeTracker()
  if (!document.hidden) {
    await this.waitStart()                       // poll canStart every 100ms
    return this._start(...args)
  } else {
    return new Promise((resolve) => {            // defer WHOLE start until visible
      const onVisibilityChange = async () => {
        if (!document.hidden) {
          await this.waitStart()
          document.removeEventListener('visibilitychange', onVisibilityChange)
          resolve(this._start(...args))
        }
      }
      document.addEventListener('visibilitychange', onVisibilityChange)
    })
  }
}
```

**Flow:** double-start refusal returns `{success:false}` instead of throwing → iframes ping the parent for an `iframeId` grant with bounded backoff (10 attempts, delay *= 1.5 from 250 ms, `stopAttempts` latch freezes once `checkStatus()` reports parent alive) → hidden tabs park the ENTIRE start behind a self-removing `visibilitychange` listener → visible tabs await `waitStart()`, a 100 ms `setInterval` poll on `canStart`. The latch is armed by exactly four paths: BroadcastChannel election `resp`/`reg` replies, the `forceSingleTab` constructor shortcut, the 250 ms fallback timeout, and parent `iframeId`/`startIframe` grants.
**Invariant:** `_start` never races the cross-tab election — no admission POST leaves before `canStart`, and never twice per instance (Active/Starting refusal precedes everything). Hidden-tab deferral is total: not even the worker 'start' message fires until the tab is shown. The visibility listener removes itself, so a tab that stays hidden forever leaks nothing but the pending promise.
**Probe:** `grep -n 'document.hidden' tracker/tracker/src/main/app/index.ts` → :1835, :1841; `grep -n 'delay \*= 1.5' …/app/index.ts` → :743 (both verified live at pin).
**Direct test:** none in-repo for this seam (App class has no suite); behavior pinned by source anchors only.

## Get live surrounding code
**Retrieve (executed):**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "waitStart canStart allowAppStart visibilitychange deferred start", limit: 6 });
```
→ rank-1/rank-2 `App.waitStart :1789-1798`, `App.allowAppStart :748-754` (line-exact).

## Verdict
Adopt the three-layer gate (idempotence refusal → visibility deferral → election latch poll) as pure lifecycle behavior. Adapt poll intervals and backoff shape to your host. Omit the iframe parent-signal loop unless you track cross-origin frames.
