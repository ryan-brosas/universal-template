<!-- capsule-v2 -->
# CDP transport `_call` — how do calls reach the wire, self-heal after a socket drop, and never leak a sessionId where Chrome refuses one?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What does the single funnel under all 652 generated wrappers guarantee about reconnection, session routing, and observation?

## One funnel, reconnect-once, browser-level exemption, immutable observed params
**Path/Symbol:** `skills/cdp/sdk/session.ts:Session._call` (:331-379), `onMessage` (:381-395), `isBrowserLevel` (:409-412).
**Signature:** `_call(method: string, params?: unknown, opts?: { sessionId?: string }, reconnected = false): Promise<unknown>`.
**Data Shape:** params defaults `{}`; response promise resolves `m.result` or rejects `CdpError(code, message, data)` built from `m.error` in `onMessage`; pending map keys are monotonically increasing wire ids.

### Decisive source
```ts
if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
  if (reconnected) return Promise.reject(new Error('Not connected. Call session.connect(...) first.'));
  return this.connect().then(() => this._call(method, params, opts, true));
}
const id = this.nextId++;
const msg: Record<string, unknown> = { id, method, params: params ?? {} };
const sid = opts?.sessionId ?? this.activeSessionId;
if (sid && !isBrowserLevel(method)) msg.sessionId = sid;
...
const observedParams = (JSON.parse(wire) as { params?: unknown }).params ?? {};
```
with `function isBrowserLevel(m: string) { return m.startsWith('Browser.') || m.startsWith('Target.'); }`

**Flow:** dead-socket check → one reconnect retry (guarded by the `reconnected` flag, so a failed retry rejects cleanly instead of looping) → assign id → inject the caller-supplied sessionId or the active pointer, EXCEPT for `Browser.*`/`Target.*` which are browser-level and reject a sessionId → send wire JSON → correlate the reply by numeric id → if an observer is installed, await it bounded to 5s and swallow its failures.
**Invariant:** (1) reconnect happens at most once per call — a stale flat sessionId surfaces Chrome's own clean `CDP -32001: Session with given id not found` (target persists; re-attach), never a wrong-target action. (2) `Target.attachToTarget`/`Target.getTargets`/`Browser.*` MUST go out without `sessionId` — injecting one there breaks the call; any porter adding fields to the envelope must preserve the `isBrowserLevel` exemption. (3) the observer sees `observedParams`, a fresh parse of the serialized wire, because the caller can mutate the object it passed while Chrome is still processing. (4) observer latency is capped at 5s so a stalled screenshot/disk write can never leave a successful protocol action unresolved, and observer throws never propagate.
**Probe:** `skills/cdp/sdk/session.test.ts` covers candidate discovery only; behavior here is pinned deterministically — `grep -n "isBrowserLevel\|reconnected" skills/cdp/sdk/session.ts` pins the exemption (:345, :410-412) and single-retry gate (:338-341).
**Coverage caveat:** no direct unit test drives `_call`; treat the excerpt above as ground truth.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "_call", limit: 5, fields: ["signature", "name", "file"] });
// resolves browser-harness-js.skills.cdp.sdk.session.Session._call @ session.ts:331-379
```

## Verdict
Adopt the reconnect-once transport contract, the browser-level sessionId exemption, and immutable observed params for any thin CDP/WebSocket bridge; adapt the 5s observer bound to your diagnostics budget; omit the Dia-specific pieces of connect (see `websocket-lifecycle-guard`) when you have no prompt-gating browser. Caveat: direct tests cover only `getBrowserCandidates`; everything here was confirmed by whole-file source reading.
