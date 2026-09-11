<!-- capsule-v2 -->
# Drainable signal queue — how do you turn dozens of raw CDP events per action into the handful that change what to do next?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How does the agent get a compact steering digest (dialogs > crash > download > navigation) without drowning in event spam?

## One idempotent subscriber, handler-table → one-line messages, splice-drain, active-session filter
**Path/Symbol:** `skills/cdp/sdk/helpers.ts:SIGNAL_HANDLERS` (:142-160), `attachSignals` (:162-178), `drainSignals` (:180-183), `detachSignals` (:185-190); `_lastDialog` feeds `pageInfo`.
**Signature:** `attachSignals(): void` (idempotent via `_signalsAttached`) · `drainSignals(): string[]` (auto-attaches, returns and CLEARS) · `detachSignals(): void`.
**Data Shape:** queue is a plain `string[]`; each message is one human-readable line, e.g. ``dialog confirm: "Leave?"``, `download start: file.mp4`, `target CRASHED: url`, `navigated -> url`. Progress events with `state === 'inProgress'` return `null` = suppressed; only terminal states surface.

### Decisive source
```ts
_sigOff = session.onEvent((method: string, p: any, sid?: string) => {
  if (sid && sid !== active() && method.startsWith('Page.')) return;  // other tabs' Page.* events are noise
  const fn = SIGNAL_HANDLERS[method];
  if (!fn) return;
  try { const m = fn(p); if (m) _signalQueue.push(m); }
  catch { /* Never let a subscriber throw into the event loop. */ }
});
```
Handler table keys — the whole curation policy in nine lines:
`Page.javascriptDialogOpening` (stores `_lastDialog`, emits) · `Page.javaScriptDialogClosed` (clears it, emits nothing) · `Page.fileChooserOpened` · `Page.downloadWillBegin` (remembers name) · `Page.downloadProgress` · `Page.windowOpen` · `Page.frameNavigated` · `Target.targetCreated/targetDestroyed/targetCrashed` · `Network.loadingFailed`.

**Flow:** attach once per task (BEFORE the action whose fallout you want — pre-attach events are lost forever) → act → settle ~300ms (events land after your snippet returns) → `drainSignals()` splices the buffer → react dialog > crash > download-complete > navigation > rest.
**Invariant:** (1) attach/drain ordering: a drain that auto-attaches on first call still misses everything fired before it. (2) The `sid !== active() && method.startsWith('Page.')` filter is what keeps background tabs you opened from steering the current step — `Target.*` events are browser-level (`sid === undefined`) and always pass. (3) Subscriber exceptions are swallowed inside the listener; one bad handler can't kill the stream. (4) `_lastDialog` is dual-purpose: cleared by `javaScriptDialogClosed`, read by `pageInfo()` when its eval times out so `{dialog}` is reported instead of a hang.
**Probe:** no direct test (needs live browser events). Deterministic probe: `grep -n "SIGNAL_HANDLERS\|_signalQueue.splice" skills/cdp/sdk/helpers.ts` (:142, :182); docs contract `interaction-skills/agent-signals.md` matches the table 1:1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "drainSignals", limit: 3, fields: ["signature", "name", "file"] });
// resolves helpers.drainSignals @ helpers.ts:180-183
```

## Verdict
Adopt the drainable-digest pattern for ANY high-frequency event bus an LLM consumes; adapt the handler table to your domain's "what changes the next action" events; omit the cross-tab filter only if you're single-target. The null-means-suppress convention for progress spam is worth keeping verbatim.
