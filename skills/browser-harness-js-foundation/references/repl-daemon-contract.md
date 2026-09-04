<!-- capsule-v2 -->
# REPL Daemon Contract — HTTP-eval daemon over a persistent CDP session

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha). LIVE-EXERCISED this pass (probes below ran through the real daemon).

## Question
What is `browser-harness-js` (the binary every skill calls), and which of its contracts must a port preserve?

## Path / Symbol
- Wrapper: `skills/cdp/sdk/browser-harness-js` (bash, 4.8KB): port default **9876**, health probe, nohup start, stdin→POST /eval.
- Daemon: `skills/cdp/sdk/repl.ts` (218L): POST /eval (raw JS body, NOT JSON-wrapped), GET /health, /quit; `isExpression()` wraps bare expressions as `return (expr);` else evaluates multi-statement code inside `(async () => { ... })()`.
- Underlying: `session.ts` Session — connect auto-detect (`detectBrowsers()` most-recently-launched-first, fast per-candidate timeouts), `connectPromise` single-flight, phantom-WS close guard (only reject pendings if `this.ws === ws`).

## Signature
```bash
browser-harness-js <<'EOF'          # snippet on stdin → daemon → CDP
const t = await session.Target.createTarget({url:'about:blank', background:true});
...
return JSON.stringify(result)        # return value becomes stdout (renderResult)
EOF
# renderResult: undefined/null/""/{}/[] → EMPTY body; string → raw; else JSON.
# This is why skills end snippets with explicit `return JSON.stringify(...)`
# and why ytdl checks `case "$raw" in *'"ok":true'*)` for success.
```

## Data Shape
/health returns `{ok, version, uptime, connected, sessionId}`; version read from disk each wrapper call while the daemon boot-caches its own — "a mismatch reveals a stale running daemon" (wrapper comment :26-28). Global helpers injected into eval scope: `cdp(sessionId, method, params)`, `session`, `axView`, recording helpers, Generated domain bindings.

## Decisive source
repl.ts :108-127 (`isExpression`, `runSnippet`) and :135-147 (`renderResult` docstring quoted above); session.ts :104-156 (auto-detect ladder + candidate error report "click Allow on its remote-debugging prompt"); :157-186 (openWs with timeout + Dia-only macOS auto-Allow keystroke injection gated on `name==='Dia' && platform==='darwin'`). The stderr note in ytdl/ttdl ("the REPL daemon's stderr isn't wired to this CLI") explains the `_stats` channel pattern.

## Flow / Invariant
1. One daemon per user/host holds THE browser WebSocket; every snippet is stateless except what it stashes on `globalThis` (findata's ticker map, my probes' handles).
2. Empty-body-means-falsy contract drives bash result handling — always return an explicit JSON marker.
3. Connect is idempotent and single-flight; snippets reconnect defensively because a dropped WS heals on next call.

## Probe (direct tests)
Live at this pin: started daemon against headless Chromium/151 (`--start` → `{"ok":true,"version":"0.9.0"}`), connected via `session.connect({port:9333})`, executed create/navigate/lifecycle-wait/evaluate (example.com title round-tripped correctly) and the full MSE capture probe through `/eval`. Health endpoint observed transitioning `connected:false → true`.

## Retrieve
`codebase-memory-mcp cli search_graph --project browser-harness-js --query "resolveWsUrl"` → entry points list session surface.

## Verdict
ADOPT: HTTP-daemon-over-CDP with expression/statement dual evaluation and empty-body semantics is the whole reusable contract.
