<!-- capsule-v2 -->
# Claude Code WebSocket hello ladder — how do you complete a bridge handshake against a slow sandbox without missing a hello that lands immediately after open?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The bridge announces readiness with a post-connect `bridge-hello` frame, but sandboxes are slow and the frame can arrive in the same microtask burst as `open` — how do you time the handshake so neither case is missed?

## Dual-flag resolution + deadline-shrinking timeouts + bounded backoff
**Path/Symbol:** `packages/harness-claude-code/src/claude-code-harness.ts` — `openWebSocketAndWaitForBridgeHello` (:1271–1380), `openBridgeWebSocket` (:1382–1417).
**Signature:** `openBridgeWebSocket({endpoint, timeoutMs, onHello}): Promise<WebSocket>`; inner `openWebSocketAndWaitForBridgeHello({endpoint, openTimeoutMs, getHelloTimeoutMs, onHello}): Promise<WebSocket>`.
**Data Shape:** per-attempt flags `opened` / `sawBridgeHello` / `settled`; two unref'd timers (open, hello); shared deadline `Date.now() + timeoutMs`; attempt counter; lastError.

### Decisive source
```ts
// claude-code-harness.ts:1313–1338 — resolve ONLY when both flags hold
const tryResolve = () => {
  if (opened && sawBridgeHello) settle();
};
const startHelloTimer = () => {
  if (helloTimer) return;
  const helloTimeoutMs = getHelloTimeoutMs();   // evaluated AT OPEN time
  helloTimer = setTimeout(() => settle(new Error(
    `claude-code bridge did not send bridge-hello within ${helloTimeoutMs}ms`)), helloTimeoutMs);
  helloTimer.unref?.();
};
const onOpen = () => {
  opened = true;
  if (openTimer) { clearTimeout(openTimer); openTimer = undefined; }
  startHelloTimer();
  tryResolve();                                  // hello may already have arrived
};
// :1395–1411 — retry loop bounded by ONE shared deadline
while (Date.now() < deadline) {
  attempt++;
  try {
    const remaining = Math.max(1, deadline - Date.now());
    return await openWebSocketAndWaitForBridgeHello({
      endpoint,
      openTimeoutMs: Math.min(10_000, remaining),
      getHelloTimeoutMs: () => Math.min(5_000, Math.max(1, deadline - Date.now())),
      onHello,
    });
  } catch (err) {
    lastError = err;
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    await sleep(Math.min(250 * attempt, 1_000, remaining));
  }
}
throw new Error(`claude-code bridge did not complete WebSocket handshake within ${timeoutMs}ms after ${attempt} attempt(s). Last error: ${formatUnknownError(lastError)}`);
```

**Flow:** openBridgeWebSocket loops while the shared deadline holds → each attempt opens a socket with `openTimeoutMs = min(10s, remaining)` → on `open`, the open timer is cleared and the hello timer starts with `getHelloTimeoutMs()` evaluated AT OPEN time, so the hello budget shrinks as the deadline approaches → resolution requires BOTH `opened` AND `sawBridgeHello` (the hello may land in the same microtask burst as open — tryResolve is called from both handlers) → the hello message is parsed for `type:'bridge-hello'` and its `capabilities.experimental_userMessageResponses === true` is read exactly once into onHello, gating steering availability → close-before-hello, socket error, or either timeout settles rejection and TERMINATES the socket → failed attempts sleep `min(250·attempt, 1000, remaining)` before retrying → exhaustion throws with attempt count + last error.
**Invariant:** a socket that opened but never helloed is NEVER returned (dual-flag gate); the hello budget shrinks from the shared deadline rather than resetting per attempt (no unbounded total wait); every failed attempt terminates its socket (no leaked connections); capability detection happens exactly once at hello time.
**Probe:** direct tests `packages/harness-claude-code/src/claude-code-harness.test.ts` describe 'bridge WebSocket startup' :856–978 — seven cases: hello immediately after open resolves without terminate (:864–877); hello capability exposes `submitUserMessage` (:879–901); `/compact keep the error trace` sent as `{type:'user-message'}` without an active turn (:903–919); open-without-hello rejects + terminates (:921–933); hello budget uses the REMAINING deadline — "did not send bridge-hello within 5ms" (:935–948); close-before-hello rejects (:950–963); open timeout rejects (:965–976).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "openBridgeWebSocket openWebSocketAndWaitForBridgeHello bridge-hello experimental_userMessageResponses", limit: 10 });
```

## Verdict
Adopt dual-flag handshake + deadline-shrinking timeouts + bounded linear backoff for any in-sandbox service whose readiness is announced post-connect; adapt the capability field names and per-attempt caps; omit the retry ladder where the transport guarantees connect==ready — opencode/codex/deepagents use a single-attempt openWebSocket with `helloTimeoutMs = min(startup, 5s)`. Bonus contract pinned here: claude-code's doCompact rides the user-message rail (`/compact [text]`, :1780–1793) because no SDK control method exists for compaction.
