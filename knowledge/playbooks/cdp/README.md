---
title: cdp
summary: 'Use for explicitly requested DevTools Protocol work or a named capability unavailable through the configured browser MCP, such as screenshots, DOM/runtime evaluation, network tracing, uploads or emulation. Ordinary browser UI reading and interaction defaults to Beacon; this persistent CDP SDK is the fallback, not a prerequisite.'
kind: playbook
setup: bash scripts/setup
compatibility: 'Requires Node 23.6+ and a Chromium-based browser. The extension relay is optional; remote debugging supports explicit endpoint or profile selection.'
---

# CDP fallback, `browser-harness-js`

For ordinary browser work, start with [Beacon MCP](../beacon/README.md). Do not install this SDK, enable debugging, relaunch a browser or run `session.connect()` merely to read or operate a page. Use this procedure when the user explicitly requests CDP or after naming a real capability/approved-connection gap in the browser MCP. Preserve the same account, approved profile and action permissions; a fallback must not bypass human-owned authentication or consent.

Custom codegen'd CDP SDK (every method from browser_protocol.json + js_protocol.json gets a typed wrapper) plus a tiny HTTP server that holds one persistent CDP `Session`. The `browser-harness-js` CLI auto-starts the server on first use and forwards JS snippets to it.

The SDK lives in this playbook's `sdk/` directory. `$SKILL_DIR` means the directory containing this `README.md`. Resolve it from the loaded playbook, not a host-specific install path. The CLI should be on PATH as `browser-harness-js`.

For progress complaints, missing flat sessions, and shared-daemon updates, use [connection guidance](interaction-skills/connection.md#health-versus-task-progress). Raw CDP remains the API; optional guards do not replace known deterministic routes.

For browser-relay MCP workflows instead of this SDK, use [beacon](../beacon/README.md).

## When to Use / NOT

- **Use when:** the user requests CDP, or the configured browser MCP lacks the needed protocol capability or cannot reach the approved browser. Examples include screenshots, computed styles/DOM evaluation, network traces, emulation, file inputs and media capture. Name the gap before using this fallback.
- **NOT when:** ordinary page reading, navigation, form interaction or a supported browser-MCP operation answers the task. An existing debugging port alone does not make CDP preferable. Follow [Beacon](../beacon/README.md) first; do not translate these protocol calls into invented MCP tools.

## Background-first operation

Use task-owned background targets and explicit per-target `sessionId` routing.
Page-targeted CDP input and focus emulation do not require desktop activation.
Do not bring the browser forward, move the OS pointer or copy clipboard/login
state as a routine workaround. An approved isolated/headless browser is useful
for unattended jobs, but a different profile is not an implicit permission grant.
See [connection guidance](interaction-skills/connection.md#parallel-work-background-tabs-and-desktop-focus)
for isolation and the ask-first exceptions. Disable legacy prompt auto-approval
with `autoAllow: false`; authentication and consent stay human-owned.

## How to use

Just run `browser-harness-js '<JS>'`. The first call spawns the server in the background; subsequent calls hit the same process and so reuse the same `session`, the same wire to the browser (extension relay or remote-debugging WebSocket), and any globals you set.

Connect to the approved browser as described in [Connecting](#connecting) first.
Each snippet can then own a background target without using the shared active-tab
cursor or leaving a tab open:

```bash
browser-harness-js '
const { targetId } = await session.Target.createTarget({ url: "about:blank", background: true });
const { sessionId } = await session.Target.attachToTarget({ targetId, flatten: true });
try {
  await cdp(sessionId, "Page.enable", {});
  await Promise.all([
    session.waitFor({ method: "Page.loadEventFired", sessionId, timeoutMs: 10000 }),
    cdp(sessionId, "Page.navigate", { url: "https://example.com" }),
  ]);
  return (await cdp(sessionId, "Runtime.evaluate", { expression: "document.title", returnByValue: true })).result.value;
} finally {
  await session.closeTab(targetId, sessionId);
}
'
```

Output is the **raw result content** — no `{ok,result}` envelope.

| Result type | stdout |
|---|---|
| string                       | bare text, no JSON quotes (e.g. `Example Domain`) |
| number / boolean             | `42`, `true` |
| object / array (non-empty)   | compact JSON (e.g. `{"frameId":"..."}`, `[1,2,3]`) |
| `undefined` / `null` / `""` / `{}` / `[]` | empty (no output) |

**Errors** go to **stderr**, exit code `1`. The CDP error message and JS stack are printed verbatim, e.g.:
```
Error: CDP -32602: invalid params
    at _call (.../session.ts:117:33)
    ...
```
Detect failure with `if browser-harness-js '...'; then ...; else handle_error; fi` or by checking `$?`.

**Multi-line snippets via stdin (heredoc).** Important: a multi-statement snippet does NOT auto-return the last expression — write `return X` explicitly. Single-expression snippets passed as the first argument DO auto-return.

```bash
browser-harness-js <<'EOF'
const tabs = await listPageTargets();
return { pageCount: tabs.length }; // Read-only example; do not select the first user's tab.
EOF
```

## CLI commands

| Command | Behavior |
|---|---|
| `browser-harness-js '<js>'`     | Auto-start server if needed, eval the JS, print result. |
| `browser-harness-js <<EOF…EOF`  | Same, code from stdin. |
| `browser-harness-js --status`   | Print health JSON (version, uptime, connected, transport, extension, sessionId) or exit 1 if down. |
| `browser-harness-js --version`  | Print the SDK version from the on-disk files (no daemon needed). |
| `browser-harness-js --start`    | Explicit start (no-op if already running). |
| `browser-harness-js --stop`     | Graceful shutdown. Drops session state. |
| `browser-harness-js --restart`  | Stop + start fresh. |
| `browser-harness-js --logs`     | `tail -f` the server log (`/tmp/browser-harness-js.log`). |
| `browser-harness-js recordings [--latest\|enable\|disable\|replay [dir]]` | Show recording status, persist local consent, or replay an rrweb recording. |
| `browser-harness-js --no-auto-allow '<js>'` | Set `session.autoAllow = false` on the daemon, then eval the JS. Clears any explicit opt-in to Dia prompt keystrokes. New sessions already default to `autoAllow: false`. |

Env vars: `CDP_REPL_PORT` (default `9876`; the extension worker hardcodes 9876 — keep them in sync), `CDP_REPL_LOG` (default `/tmp/browser-harness-js.log`), `CDP_RECORD` (`1`/`0` preference override), `CDP_RECORDINGS_DIR` (storage override), `BROWSER_HARNESS_JS_HOME` (state root, default `~/.browser-harness-js`).

## Guarded interaction at unknown UI boundaries

Prefer the exact deterministic API/CDP route when known. At an **unknown UI decision
boundary**, default to guarded **observe → act → verify**. Raw CDP, AX and vision
helpers remain intentional escape hatches for unsupported mechanics, never a way
to bypass a denial or required approval. The controller is model-neutral; Jev is
optional, and model confidence is **not** permission.

`InteractionController` is importable from `sdk/interaction.ts`. REPL globals:
`InteractionController` and `createInteractionController({allowedOrigins, input?})` (uses
the persistent transport, **never** its mutable active-target pointer).
`input: 'trusted'` opts into real CDP mouse/keyboard input (see below).

```bash
browser-harness-js <<'EOF'
// session must already be connected to the authorized browser.
// Choose the target from an authorized tab listing, not tab-strip position.
const { sessionId } = await session.Target.attachToTarget({ targetId: globalThis.authorizedTargetId, flatten: true });
globalThis.guard = createInteractionController({ allowedOrigins: ['https://example.com'] });
globalThis.guardScope = { sessionId };
globalThis.seen = await guard.observe({ scope: guardScope, maxElements: 64 });
return seen;
EOF
```

Choose only an offered candidate/operation consistent with the user's authority;
never choose the first candidate just because it exists. Then, in a later snippet:

```js
const receipt = await guard.act({
  scope: guardScope, observationId: seen.observationId,
  action: { targetId: chosenCandidateId, operation: 'click' }
});
// Only after an executed receipt, inspect the changed state (not proof of success):
if (receipt.status !== 'executed') return receipt;
return await guard.waitForChange({ scope: guardScope, revision: seen.revision, timeoutMs: 5000 });
```

- `observe({scope:{sessionId},maxElements?}, {signal?}?)` returns `{scope,
  observationId,revision,candidates:[{id,role,label,operations,value?,checked?,selected?,expanded?,options?,context?}],
  url,title,truncated,truncation:{elements,scan,text}}`. Default 64 candidates, maximum 128; scan cap
  4096 light-DOM elements. Labels/title/URL are bounded to 256/512/2048 characters.
  IDs are opaque, observation-scoped handles, not backend node IDs or locators.
- `act({scope,observationId,action:{targetId,operation,text?,option?,key?}}, {signal?}?)`
  returns `{status,reason?}`. **One attempted action consumes the observation**;
  observe again before any next attempt. New observations invalidate previous
  handles in the same scope. Scope mutations are serialized across controllers
  sharing a Session; separate aliases/attachments are not a global browser lock.
- Candidates come from native controls (buttons, links, text/search/url/number
  inputs, textareas, checkboxes, radios, single `<select>`) and allowlisted ARIA
  roles on any element: `button link checkbox radio switch tab menuitem
  menuitemcheckbox menuitemradio option treeitem combobox textbox searchbox`.
  Unknown roles are not guessed at. Names follow ARIA precedence:
  `aria-labelledby` (up to 8 ids), `aria-label`, `<label>`, then title/placeholder
  for fields or name-from-content for clickable roles: descendants contribute
  their own `aria-label`/`aria-labelledby`/`alt`, hidden subtrees contribute
  nothing (bounded to 256 nodes), so a calendar day showing "20" is named
  "Tuesday, October 20, 2026". States: `checked` (native or `aria-checked`),
  `selected` (`aria-selected` on options/tabs), `expanded` (`aria-expanded`),
  `value`, and `options` (a `<select>`'s first 64 option labels). `context` is the
  nearest *named* dialog, grid, group, listbox, menu, form, region... around the
  target (e.g. `dialog: Departure date`), which disambiguates repeated labels.
- Controls inside open shadow roots are observed; hidden/inert/disabled ancestors,
  hit tests and containment cross shadow boundaries.
- A control is actionable at the first unobstructed point among nine samples
  (center first), so partly covered controls work; trusted input clicks that
  point. A `pointer-events: none` control (an accessibility overlay over its row)
  counts as clear when the hit lands inside its own parent component; a foreign
  overlay (e.g. a modal) still blocks.
- Scrolling: when the page scrolls, a `page` candidate (last slot, labelled by
  the title, `value` like `35% scrolled`) offers `scroll_down`/`scroll_up`;
  visible scroll containers that are named or have a list/dialog/grid/region/menu/
  tree/tabpanel/feed/log role are candidates too. Each scroll moves 80% of the
  visible height; clipped or offscreen controls appear in the next observation.
- Operations are offered per candidate; use only those listed:
  - `click`: synthetic DOM `click()` by default; a real mouse move/press/release
    at the freshly rechecked center with `input: 'trusted'`.
  - `type` (`text`): **replaces the entire value**, maximum **4096** characters.
    Synthetic mode uses the native setter and one bubbling `input` event (no focus,
    keys, `change` or submit). Trusted mode focuses the target, selects its whole
    content and inserts the text as real input, which also works for
    contenteditable textboxes (offered only in trusted mode).
  - `select` (`option`): sets a native `<select>` to `options[option]` and emits
    `input` and `change`.
  - `scroll_down`/`scroll_up`: page and scroll-container candidates only.
  - `press` (`key`, trusted only): focuses the target, then sends one key from
    `Enter Escape Tab Backspace Delete ArrowUp ArrowDown ArrowLeft ArrowRight Home
    End PageUp PageDown Space`. Use it for autocomplete lists (type, ArrowDown,
    Enter) and form submission.
- Trusted input is the only way to drive widgets that ignore synthetic events
  (pointerdown handlers, keyboard-driven comboboxes). The page rechecks the target
  immediately before reporting its point; a script may still move content during
  the one CDP round trip before the input lands. Trusted mode also enables focus
  emulation so background tabs accept focus and keys.
  Password, sensitive autocomplete and marked-private controls are excluded, as
  are conservative sensitive name/id/label/title/placeholder matches (e.g. token,
  PIN, payment, account, email/address). These heuristics can overexclude and are
  not general DLP: ordinary page text, URL/title and unrecognized secrets may remain.
  Oversized values/identities are omitted with `truncation.text`, never acted on
  using a partial fingerprint. Exact fingerprints stay in-page (8192 characters
  per target); only SHA-256 digests cross CDP (at most 8192 digest characters).
  Hashing requires in-page SubtleCrypto, normally HTTPS or localhost; unavailable
  crypto rejects observation rather than weakening identity checks.
- `waitForChange({scope,revision,timeoutMs?}, {signal?}?)` returns
  `{changed,observation}` with the same observation shape, including on timeout.
  Default 5000 ms, range 0–60000. Samples at most every 500 ms plus snapshot cost;
  it detects projected state, not arbitrary network/application success. Calls
  can await browser responses beyond this interval; use `signal` for a deadline.
- `invalidate(scope?)` expires one/all scopes; `close()` expires everything and
  removes listeners, **without** closing the Session or browser. Close is
  cooperative: queued callers cancel promptly, but already-dispatched effects
  may finish later. The shared scope queue stays quarantined until outstanding
  transport settles; late snapshot objects are released, and effects never replay.
- Bounds: 32 retained scopes and 32 concurrent waits per controller; 32 active
  queue scopes per Session and 32 pending operations per scope across controllers
  (including in-flight/cancelled-but-unsettled work). Capacity rejects reads/waits
  or returns `blocked` for actions. Invalidate unused scopes to free retained
  observations. Stalled releases also backpressure observations; close does not
  force-unlock unresolved transport calls.

Receipts: `executed` = dispatched, **not goal achieved**; verify by fresh state or
an authoritative read-back. `stale` → reobserve. `blocked` (especially
`origin_denied`) → approval/stop, not raw-API evasion. `outcome_unknown` → inspect,
**never blind retry**. Cancelling before dispatch prevents later effects;
cancelling after dispatch returns unknown and cannot retract browser-side work.
`observe`/`waitForChange` reject on denial, cancellation or unavailable context.

Require **1–32** exact HTTP(S) `allowedOrigins`, each at most **2048** characters
(length checked before deduplication), and a nonempty `scope.sessionId` of at most
**256** characters. Empty origin lists reject construction. No paths,
wildcards, credentials or implicit current-origin grant. Origin, document,
connection generation, native node identity, semantics/value, enabled/visible
state and center-point occlusion are rechecked before effects. Identity is what a
target means (role, full untruncated name and content, operations, options,
value/checked, and `id`/`name`/`type`/`href`/`role`/`for`/`form`/`action`);
cosmetic churn (class, style, tooltip titles, `data-*`) and layout shifts keep a
target valid, and trusted input always uses the freshly rechecked center.
Navigation, disconnect/reconnect, invalidation and replay expire handles.
Reconnect retains the selected endpoint/transport/options; reattach after a
connection change. Injected adapters should expose Session-compatible `onEvent`,
`getConnectionGeneration` and the `expectedGeneration` dispatch fence for lifecycle
invalidation; remote-object/document checks still apply to `_call`-only adapters.

Scope is still bounded: the main frame and its open shadow roots; no iframes,
closed shadow roots, canvas, multi-selects, drag or file inputs. Controls must be
visible in the viewport at some unobstructed point.
Unsupported/hidden/occluded controls are omitted. This is not a complete AX tree,
a sandbox around raw CDP, a navigation/network firewall, or an atomic GUI transaction.
The page/user may race effects and scripts may navigate after activation; every
subsequent guarded call rechecks authority. Never infer success from a receipt.
See [agent-operating-loop.md](interaction-skills/agent-operating-loop.md).

## Optional Fabric browser provider

When the optional harness-owned Pi extension is loaded (see the repository
[upstream README’s connector section](https://github.com/monotykamary/browser-harness-js/tree/12620e7e50c5eadc7dc078c210ec38a8d071d6cc#optional-pi--fabric-connector)), `browser-harness` provides
`browser` through Fabric's normal component protocol. It is not built into Fabric
and needs no Jev/model. If the definition is unknown, request extension loading;
configuration may remain `waiting` for `component:browser-harness` until then.
Do not try to repair this with a browser connection or a Fabric-private import.

Inspect `components.describe({component:"browser-harness"})`, then
`components.plan({entries:[{id:"browser",component:"browser-harness",config}]})`.
Inspect the plan and obtain any required approval before
`components.apply({...plan.request,expectedRevision:plan.revision})`.
Configuration requires trusted `modulePath` (SDK `session.ts`), explicit `wsUrl`
and exact `allowedMethods`; guarded use additionally requires trusted
`interactionModulePath` (SDK `interaction.ts`) and exact `allowedOrigins`.
Paths resolve relative to invocation cwd; `callTimeoutMs` defaults to 10000
(range 100–60000). No implicit endpoint, origin, prompt approval or grants.

Registration/activation do not connect. Explicit `browser.connect` acquires the
session with `autoAllow:false`. Separately grant `Target.attachToTarget` if needed
to attach a known authorized target on that connection; use its returned
`sessionId` for every guarded `scope`. `allowedMethods:[]` removes `browser.cdp`;
raw grants, when present, are **not origin-limited** and invalidate observations.
`browser.observe`, `browser.act`, `browser.waitForChange` use the guarded shapes
and receipt rules above. Close is owned by the component's provider lifecycle.

## API surface inside snippets

These globals are pre-loaded — no imports needed:

- `session` — the persistent `Session`. Has every CDP domain mounted: `session.Page`, `session.DOM`, `session.Runtime`, `session.Network`, … 56 domains, 652 methods total.
- `listPageTargets()` — list real page targets via CDP's `Target.getTargets` (works on Chrome 144+ too), with `chrome://` and `devtools://` URLs filtered out. No args — uses the connected session. Over the extension, entries also include strip `index`, `windowId`, `groupId`, `pinned`, `muted`, `active`.
- `ext` — Chrome-extension commands (extension transport only): tab groups, pin/mute/move/discard/reload/duplicate, windows. See [connection.md](interaction-skills/connection.md). `session.Browser.getWindowForTarget` / `getWindowBounds` / `setWindowBounds` / `grantPermissions` work over the extension too. OOPIF and worker targets use UUID `targetId`s from `Target.getTargets`.
- `detectBrowsers()` — scan OS-specific profile dirs for running Chromium-based browsers with remote debugging on. Returns `[{name, profileDir, port, wsPath, wsUrl, mtimeMs}]`, sorted by most recently launched.
- `resolveWsUrl(opts)` — resolve a WS URL from `{wsUrl}` | `{port, host?}` | `{profileDir}`. For the no-args auto-detect flow, call `session.connect()` directly instead.
- `CDP` — the generated namespaces (`CDP.Page`, `CDP.Runtime`, …) for type-name reference.
- `axView(nodes, opts?)` — compressed accessibility-tree view: a pure projection over a raw `Accessibility.getFullAXTree`/`queryAXTree` result. Drops ~96% structural noise, assigns `[n]` refs → `backendDOMNodeId`. Options: `{ interactive, refs, maxDepth, redactSensitive, locators }` (`locators: true` emits a stable `loc=role:R["N"]` per ref usable across re-snapshots — see `interaction-skills/snapshot.md`).
- `axDiff(prev, next)` / `parseAxRefs(view)` / `axClick(ref, refs?)` / `axType(ref, refs, text)` — multi-step snapshot helpers (diff, ref map, click/type by ref). See `interaction-skills/snapshot.md`.
- `parseAxLocators(view)` / `resolveLocator(loc)` / `isLocatorString(s)` — locator helpers. `axClick` accepts a locator string in its first arg `axClick('role:button["Submit"]')` and resolves it; `resolveLocator` returns the `backendDOMNodeId` (tries `queryAXTree` then falls back to a full-tree scan when the served Chromium hangs the former). Locators survive refMap rebuilds; `[n]` refs do not.
- `attachSignals()` / `drainSignals()` / `detachSignals()` — drainable async event queue. `drainSignals()` returns + clears a compact digest of dialogs / downloads / navigations / crashes (auto-attaches on first call; call `attachSignals()` BEFORE an action whose events you want to capture). See `interaction-skills/agent-signals.md`.
- `pageInfo({ timeoutMs? })` — `{ url, title, w, h, sx, sy, pw, ph }` via a timed `Runtime.evaluate`; returns `{ dialog }` when a native modal blocks page JS, or `{ unresponsive }` if the eval hung with no dialog.
- `help(name?)` — usage string for a helper; pass no name for the list.
- `listLearnings()` / `learnings(domain, tool?, args?)` — per-site recipe registry over `knowledge/playbooks/cdp/learnings/<domain>/manifest.json` (`nodeTools` and `browserTools` declared per manifest). See `learnings/README.md`.
- `cdp(sessionId, method, params)` — call any CDP method on an **explicit** `sessionId` without touching the active-session pointer: `cdp(sid, 'Page.enable', {})`. The multi-tab primitive: the one-tab-per-call skills route every call this way so concurrent tabs never race `session.use`. Equivalent to `session._call(method, params, { sessionId })`.
- `session.closeTab(targetId, sessionId?)` — close a tab and detach: `window.close()` on the session, then `Target.closeTarget`. Fire-and-forget in a `finally` (`.catch(() => {})`) so cleanup is guaranteed and never blocks the return. Closes are serialized.
- `startRecording(name?, title?)` / `stopRecording()` / `recordingStatus()` — consent-based rrweb DOM recording (not screenshots). Snake-case `start_recording` / `stop_recording` aliases are also available. See `interaction-skills/make-video.md`.

### Recordings

Fresh installs do **not** record. A natural request to record, show, demo, or replay opts in for that task; ordinary browser work does not. Connect first, start before the work, retain the exact returned directory, and stop after the outcome:

```js
await session.connect({ autoAllow: false })
const recordingDir = await startRecording('demo', 'Verify the account settings')
// Drive the page (or let the user). rrweb records DOM mutations in-page.
await stopRecording()
return recordingDir
```

There is no screenshot / edit-brief / MP4 pipeline. Replay with `browser-harness-js recordings replay <dir>`. Input values are masked during capture; the rest of the DOM is stored as-is under `~/.browser-harness-js` and requires consent. Never reenact a completed task to manufacture missing footage. See [`make-video.md`](interaction-skills/make-video.md).

### Calling a CDP method

Every method takes a single object argument matching the CDP wire params; it resolves to the typed return value (no `result` envelope, no `id` correlation — handled for you).

```js
// no params
await session.DOM.enable()

// required params
await session.Page.navigate({ url: 'https://example.com' })

// all-optional params (object also optional)
await session.Page.captureScreenshot()
await session.Page.captureScreenshot({ format: 'png', quality: 80 })

// returns are stripped to the typed shape
const { root } = await session.DOM.getDocument()
const { nodeId } = await session.DOM.querySelector({ nodeId: root.nodeId, selector: 'h1' })
```

### Interaction skills (recipes) — explore the folder

`interaction-skills/` holds pure-CDP recipes for mechanics that aren't obvious from the method list alone — dropdowns, drag-and-drop, OOPIFs, network waits, screenshots, recording cross-tab user actions, navigating + waiting for load, reading a JSON URL, recording media. The set grows, so **look, don't recall**: when a task isn't a straight method call (a framework that swallows clicks, a shadow-DOM trap, a wait-with-timeout, multi-tab anything), browse before improvising.

Start here for the patterns every skill shares: [`lifecycle-readiness.md`](interaction-skills/lifecycle-readiness.md) (navigate + wait for load, the one-tab-per-call shape), [`json-navigation.md`](interaction-skills/json-navigation.md) (read a JSON URL), [`media-capture.md`](interaction-skills/media-capture.md) (record `MediaSource` / hook a native API before navigate), [`make-video.md`](interaction-skills/make-video.md) (consent-based rrweb recording + replay).

```bash
ls $SKILL_DIR/interaction-skills/
grep -l <keyword> $SKILL_DIR/interaction-skills/*.md
```

Each recipe leads with the shortest CDP call that works, then the trap — in `session.Domain.method(...)` form, no wrapped helpers — so it drops straight into a snippet. If the mechanic you need isn't there, that's a gap worth filing as a new recipe.

### Finding elements: accessibility tree over selectors

For a named element (a button, link, textbox, heading), prefer the accessibility tree over CSS selectors — it finds by semantic role + accessible name (Playwright's `getByRole`/`getByText` model) and crosses shadow boundaries. Two tools, by task:

- **Targeted find** (you know the role/name): `session.Accessibility.queryAXTree` — ~30 tokens. Needs a DOM `nodeId` (from `session.DOM.getDocument`) and the active session (`session.use` first; the bare `{role, accessibleName}` form errors, and the `cdp(sessionId, …)` route hangs). No `Accessibility.enable` needed.
- **Explore an unfamiliar page** (don't know what to ask for, pick from many, summarize layout): `axView(nodes, { interactive: true })` first over `session.Accessibility.getFullAXTree({})`, then full `axView(nodes)` if needed — compressed snapshot with `[n]` refs. Multi-step: keep the previous string and use `axDiff(prev, next)`.

```js
await session.use(targetId)
const { root } = await session.DOM.getDocument({})
// Targeted: find a button labeled "Submit"
const { nodes } = await session.Accessibility.queryAXTree({ nodeId: root.nodeId, role: 'button', accessibleName: 'Submit' })
const node = nodes.find(n => !n.ignored)   // node.backendDOMNodeId → DOM.getBoxModel → Input.dispatchMouseEvent

// Explore: interactive-first compressed snapshot
const { nodes: ax } = await session.Accessibility.getFullAXTree({})
return axView(ax, { interactive: true })
```

Use DOM queries (`DOM.querySelector`, `Runtime.evaluate` with `querySelector`) for structural context, when the tree returns nothing (canvas, non-semantic divs), or when you already have a stable selector. Full guides: [`accessibility-tree.md`](interaction-skills/accessibility-tree.md) (queryAXTree) and [`snapshot.md`](interaction-skills/snapshot.md) (axView).

### Connecting

Reuse an authorized connection; do not repeatedly reconnect or request desktop
focus. For a new connection, select the approved endpoint/profile explicitly and
set `autoAllow: false`. Use the extension only when its browser identity matches
the approved task. Automatic discovery is a capability, not authority to choose
whichever browser was launched most recently.

```js
// Values come from the task's approved browser, not an arbitrary discovered tab.
await session.connect({ profileDir: approvedProfileDir, autoAllow: false })
// Or pin its already verified remote-debugging endpoint:
await session.connect({ wsUrl: approvedWsUrl, autoAllow: false })
// Extension-only, after verifying the approved browser identity:
await session.connect({ transport: 'extension', autoAllow: false })
```

`detectBrowsers()` lists running debugging candidates without selecting one.
`/health` reports transport/connection state, not permission or task success.
An existing `DevToolsActivePort` file does not prove the endpoint is live.
The connection defaults to a 5-second open timeout; when the user has agreed to
a human-owned Allow step, pass a bounded longer timeout such as `30000`.

The maintained SDK defaults to `autoAllow: false`; older installations may not.
Keep the explicit false option for compatibility. The legacy macOS Dia helper
remains an opt-in API, but this workflow must not automate Allow, login or consent. A refused or missing connection is a blocker, not permission to
relaunch a personal browser or switch profiles. Detailed transport, discovery
and recovery mechanics live in [connection.md](interaction-skills/connection.md).

### Picking a target (tab)

After `connect()`, call `session.use(targetId)` once; subsequent page-level calls (Page/DOM/Runtime/Network/etc.) auto-route to that target's sessionId. `Browser.*` and `Target.*` calls always hit the browser endpoint.

```js
// Create a task-owned background target rather than taking the first user tab.
const { targetId } = await session.Target.createTarget({ url: 'about:blank', background: true })
const { sessionId } = await session.Target.attachToTarget({ targetId, flatten: true })
await cdp(sessionId, 'Page.enable', {})
await cdp(sessionId, 'Page.navigate', { url: 'https://example.com' })
// Wait for the task's readiness signal and verify the result; close only this owned tab.
```

`listPageTargets()` uses CDP's `Target.getTargets` (not `/json`), so it works on Chrome 144+ too. It already filters out `chrome://` and `devtools://` URLs. Equivalent raw call:

```js
const { targetInfos } = await session.Target.getTargets({})
const tabs = targetInfos.filter(t => t.type === 'page' && !t.url.startsWith('chrome://') && !t.url.startsWith('devtools://'))
```

To switch tabs: `session.use(otherTargetId)`. To detach: `session.setActiveSession(undefined)`.

For a fresh tab per call (the skill pattern — safe to run in parallel), route each call to an explicit `sessionId` with the `cdp(sessionId, method, params)` global and clean up with `session.closeTab(...)` in `finally`, without ever calling `session.use`. See [`lifecycle-readiness.md`](interaction-skills/lifecycle-readiness.md) (One tab per call).

### Events

```js
// Subscribe (returns an unsubscribe fn)
const off = session.onEvent((method, params, sessionId) => { ... })

// Or wait for a single matching event with optional predicate + timeout
await session.Network.enable()
const ev = await session.waitFor(
  'Page.frameNavigated',
  (p) => p.frame.url.includes('example.com'),
  10_000
)
```

### Persisting state across calls

Each snippet runs inside its own async wrapper, so its `let`/`const` declarations vanish when it returns. To carry ad-hoc data forward, attach it to `globalThis`:

```bash
browser-harness-js 'globalThis.exampleNotes = { purpose: "research" }'
browser-harness-js 'globalThis.exampleNotes'
```

Use a caller-owned key for real concurrent workflows; a shared global name is not
isolation. Keep each task's returned target/session identifiers, rather than
mapping all user tabs to numbered globals or reusing a shared active-tab cursor.

`session` itself, the active sessionId, and event subscribers are already preserved by the server — globals are only needed for ad-hoc data.

## Connecting to a running browser (inspect flow)

1. Reuse the approved connection, or connect to the verified endpoint with
   `autoAllow: false`. No window activation is required for normal CDP work.
2. If debugging is unavailable, explain the exact connection gap. Enabling
   debugging, opening browser settings or relaunching the user's browser needs
   approval; do not perform those steps as an automatic repair.
3. Login, 2FA, debugging Allow prompts and native consent remain human-owned.
   Request the required intervention once, then verify the resulting connection.
4. Preserve the profile and account boundary. A disposable isolated/headless
   profile is appropriate for authorized tests; it does not inherit permission
   to copy the user's cookies or run an authenticated task under another identity.

## Working with targets (tabs)

- **CDP target order ≠ visible tab-strip order.** When the user says "the first tab I can see", use a screenshot or page title to identify it — `Target.activateTarget` only switches to a known targetId.

## Looking up a method

The full typed surface is in `$SKILL_DIR/sdk/generated.ts` (~655 KB, only loaded if you read it). Each method has its CDP description as a JSDoc comment plus typed `*Params` / `*Return` interfaces in per-domain namespaces.

```bash
grep -n "navigate" $SKILL_DIR/sdk/generated.ts | head
```

## Regenerating the SDK

When the upstream protocol JSONs change, replace `sdk/browser_protocol.json` and/or `sdk/js_protocol.json` and re-run:

```bash
cd $SKILL_DIR/sdk && node gen.ts
browser-harness-js --restart   # pick up the new bindings
```

Reinstalling (`npx skills add`) updates the files on disk but not the long-lived daemon — a newly-documented global then throws `ReferenceError: <global> is not defined` until you `--restart`. Compare `browser-harness-js --version` (disk) to the `version` in `--status` (daemon memory) to detect it; see [Connection: Stale daemon](interaction-skills/connection.md).

## Files

All paths are relative to `$SKILL_DIR` (the install path — see top of this doc).

- `/usr/local/bin/browser-harness-js` → `$SKILL_DIR/sdk/browser-harness-js` (the CLI)
- `sdk/repl.ts` — HTTP server (`node:http` on `127.0.0.1:9876`)
- `sdk/session.ts` — `Session` class (transport, pinned reconnect, generation tracking, target routing, events)
- `sdk/interaction.ts` — model-neutral `InteractionController`: guarded explicit-scope observe/act/wait
- `sdk/axview.ts` — `axView` / `axDiff` / `parseAxRefs`: compressed accessibility-tree projection + helpers, injected as globals (see `interaction-skills/snapshot.md`)
- `sdk/recording.ts` — consent preferences, pinned rrweb fetch/cache, injection, event storage, local replay server
- `sdk/rrweb-replay.html` — local player UI served by `recordings replay`
- `sdk/generated.ts` — codegen output: every CDP method as a typed wrapper
- `sdk/gen.ts` — codegen script
- `sdk/{browser,js}_protocol.json` — upstream protocol (vendored)
- `interaction-skills/` — CDP how-to guides (screenshots, tabs, network requests, lifecycle readiness, JSON navigation, media capture, etc.)

## Upstream

Synced from [Tom's browser-harness-js](https://github.com/monotykamary/browser-harness-js/tree/12620e7e50c5eadc7dc078c210ec38a8d071d6cc/skills/cdp) at `12620e7e50c5eadc7dc078c210ec38a8d071d6cc`, SDK `0.16.0`.
Local patch `0.16.1` disables OS consent keystrokes by default and tests that the default survives reconnects.
Local adaptations: upstream `SKILL.md` becomes this playbook `README.md`; setup and repository paths are portable; connection health/task-progress guidance is retained; background-first routing and human-owned consent qualify the legacy connection/foreground recipes; the operating-loop mechanics match the current controller. The optional Pi connector lives in the upstream repository and is not installed by this sync. Updating these files neither switches a PATH symlink nor restarts an existing daemon.
