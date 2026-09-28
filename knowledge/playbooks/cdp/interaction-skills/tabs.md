# Tabs

Keep automation in task-owned background targets. CDP routing does not require
visible tab selection. Follow [connection guidance](connection.md#parallel-work-background-tabs-and-desktop-focus)
for profile isolation and consent; never select the first target just because
it is listed first.

## Background target with explicit routing

The Session must already be connected to the approved browser. Each concurrent
workflow owns its target and uses the returned `sessionId`, not `session.use()`'s
shared mutable cursor:

```js
const { targetId } = await session.Target.createTarget({ url: 'about:blank', background: true })
const { sessionId } = await session.Target.attachToTarget({ targetId, flatten: true })
try {
  await cdp(sessionId, 'Page.enable', {})
  await Promise.all([
    session.waitFor({ method: 'Page.loadEventFired', sessionId, timeoutMs: 10000 }),
    cdp(sessionId, 'Page.navigate', { url: 'https://example.com' }),
  ])
  // Read/act through this sessionId and verify the actual result.
  // A load event is not proof that an application's work completed.
} finally {
  await session.closeTab(targetId, sessionId)
}
```

For a known existing authorized target, attach by its observed id and keep it
open afterward unless closing it is part of the task. Single-workflow
`session.use(targetId)` changes CDP routing, not desktop focus; avoid it when
other callers share the daemon.

## Visible selection is an explicit exception

Only when the user asks to see a tab or approves a demonstrated foreground-only
step, use `Target.activateTarget` or `Page.bringToFront`. OS activation is a
separate effect and needs the same permission. An automation failure or a
background tab's existence is not permission to bring it forward.

`Target.getTargets` order is not visible tab-strip order. Identify the requested
target by URL/title, a scoped screenshot, or extension-provided window/index
metadata. Read-only OS inspection may help when visible ordering is the task;
do not switch tabs or activate a window just to discover its identity.

## Creation and readiness

Creating a target directly at a URL can return while its document is still
`about:blank`. Create blank in the background, attach, arm the readiness wait
and then navigate, as above. Use an application-specific content signal when
load/network-idle is insufficient. Opening behind the user's tab is intended,
not an error to fix by activating it.

## Traps

- `listPageTargets()` already drops `chrome://` and `devtools://`. If you call `Target.getTargets` raw, you must filter yourself, or you'll attach to a 1px omnibox popup.
- If a page reports `innerWidth=0 innerHeight=0`, you're probably attached to a non-window surface (omnibox popup, background tab that never rendered).
