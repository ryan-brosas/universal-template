<!-- capsule-v2 -->
# WebSocket open lifecycle guard — how does connect() fail fast on dead ports, survive a parallel phantom socket, and auto-dismiss Dia's Allow prompt?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What are the timeout/phantom/prompt rules a porter must copy so WS-open handling neither wedges nor kills live pending calls?

## Done-latch, phantom-WS close guard, one Dia keystroke at 600ms
**Path/Symbol:** `skills/cdp/sdk/session.ts:Session.openWs` (:167-213), `dismissDiaAllowPrompt` (:427-446), `connect`/`_connect` single-flight (:114-165).
**Signature:** `openWs(wsUrl: string, timeoutMs: number, allow?: { autoAllow: boolean; name?: string; autoAllowDelayMs: number }): Promise<void>`; default `timeoutMs = 5_000`, `autoAllowDelayMs = 600`.
**Data Shape:** resolves void on `open`; rejects with distinct messages for timeout, WS error (likely 403/port closed), and close-before-open.

### Decisive source
```ts
const finish = (err?: Error) => {
  if (done) return;                       // done-latch: first terminal event wins
  done = true;
  ...
};
ws.addEventListener('close', () => {
  // Only reject pending calls that were sent on this WebSocket.
  // A parallel connect() can create a phantom WS whose close handler
  // would otherwise nuke pending entries belonging to the active WS.
  if (this.ws === ws) {
    for (const [, p] of this.pending) p.reject(new Error('CDP socket closed'));
    this.pending.clear();
  }
  finish(new Error('WS closed before open (likely 403 or port closed)'));
});
this.ws = ws;                              // assigned AFTER listeners registered
```
and the Dia gate:
```ts
const allowTimer = allow && allow.autoAllow && allow.name === 'Dia' && process.platform === 'darwin'
  ? setTimeout(() => { if (done || allowTried) return;
      if (ws.readyState !== WebSocket.CONNECTING) return;   // prompt is up only while CONNECTING
      allowTried = true; dismissDiaAllowPrompt();           // ONE osascript Return, fire-and-forget
    }, allow.autoAllowDelayMs) : null;
```

**Flow:** create WS with listeners already registered → race `open` vs per-candidate 5s timeout vs error/close → if still `CONNECTING` at 600ms and the resolved browser name is `Dia` on darwin, fire exactly one Return keystroke at the Dia process (`allowTried` latch prevents repeats; needs macOS Accessibility — missing grant degrades to waiting out `timeoutMs`, never an error).
**Invariant:** (1) every terminal path funnels through the `finish` done-latch — no double resolve/reject. (2) A losing socket's `close` must NOT flush `pending`: only `this.ws === ws` may reject in-flight calls, or a racing second `connect()` destroys the winner's traffic. (3) Auto-dismiss is gated on browser NAME (Dia), platform (darwin), CONNECTING state, and a once-latch — never fire keystrokes blindly. (4) `connect()` is single-flight via `connectPromise` (rides an in-flight attempt; cleared after settle so later calls can reconnect); `autoAllow` persists on the Session so the auto-heal reconnect inherits it.
**Probe:** no direct test drives `openWs`. Deterministic probes: `grep -n "this.ws === ws\|allowTried\|connectPromise" skills/cdp/sdk/session.ts` pins all three guards (:201-209, :192-197, :117-130).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "dismissDiaAllowPrompt", limit: 3, fields: ["signature", "name", "file"] });
// resolves session.dismissDiaAllowPrompt @ session.ts:434-446
```

## Verdict
Adopt the done-latch + phantom-close-guard + single-flight connect as a unit whenever you hand-roll a long-lived WebSocket client; adapt the 600ms prompt delay and candidate timeout to your latency budget; omit the osascript/Dia branch entirely outside macOS+Dia. Coverage caveat: source-pinned only.
