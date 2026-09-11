<!-- capsule-v2 -->
# Navigate-and-wait readiness ladder — what is the reliable "page is ready" signal, and when must you abandon it?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How does every skill in the repo wait for a page without racing or hanging?

## setLifecycleEventsEnabled + arm-before-navigate + networkIdle, content-poll fallback
**Path/Symbol:** `skills/cdp/interaction-skills/lifecycle-readiness.md` (canonical recipe :7-36); live instance `skills/gsearch/scripts/gsearch` heredoc; primitives `session.ts:waitFor` (:292-328).
**Signature:** `session.waitFor({ method: 'Page.lifecycleEvent', sessionId?, predicate?, timeoutMs? }): Promise<T>` — object form for explicit sessions, 3-arg form targets the active session.
**Data Shape:** armed BEFORE navigate; predicate `(p) => p.name === 'networkIdle'`; default timeout 30s.

### Decisive source
```js
await session.Page.enable({})
await session.Page.setLifecycleEventsEnabled({ enabled: true })   // required — without it Chrome emits ZERO lifecycleEvent
const ready = session.waitFor('Page.lifecycleEvent', (p) => p.name === 'networkIdle', 30_000)  // arm BEFORE navigate
await session.Page.navigate({ url })
await ready
```
Fallback for never-idle pages:
```js
while (Date.now() - s0 < 15_000) {
  await new Promise(r => setTimeout(r, 200))
  const { result } = await session.Runtime.evaluate({ expression: `document.querySelectorAll("<outcome-selector>").length`, returnByValue: true })
  if (Number(result.value) > 0) break
}
```

**Flow:** enable Page → enable lifecycle events ONCE per tab → create the waitFor promise WITHOUT awaiting → navigate → await it. If the page polls forever (maps, dashboards), switch to polling the cheapest DOM signal that asserts the actual OUTCOME.
**Invariant:** (1) Missing `setLifecycleEventsEnabled` = zero events = guaranteed timeout hang. (2) Arming order is load-bearing: lifecycle events fire once and a fast load can complete between `navigate()` resolving and your listener subscribing. (3) `load`/`loadEventFired` fire BEFORE SPA data renders; `networkIdle` needs a ~500ms quiet window that continuous pollers NEVER open — then only a content signal works. (4) `application/json` navigations fire NO load events at all (see json-navigation capsule). (5) Background tabs throttle timers/media — foreground (`background: true` omitted) when the page must actually play.
**Probe:** no unit test (live-browser behavior). Deterministic probe: the pattern is instantiated verbatim in `skills/gsearch/scripts/gsearch` with its trap comments; `grep -n "setLifecycleEventsEnabled" skills/gsearch/scripts/gsearch`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "waitFor", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-step ladder verbatim in any CDP driver; adapt the outcome selector to each target site; omit networkIdle ONLY for known pollers/json — and record which case applies, because silently picking `load` is how half-rendered scrapes ship.
