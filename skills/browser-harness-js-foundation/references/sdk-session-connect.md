<!-- capsule-v2 -->
# SDK Session Connect Ladder — auto-detect, single-flight, phantom-WS guard

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha). Graph-confirmed: session.ts symbols are graph entry points (resolveWsUrl, listPageTargets, detectBrowsers, getBrowserCandidates).

## Question
How does the SDK find and bind a debuggable browser, and what are the concurrency invariants?

## Path / Symbol
`skills/cdp/sdk/session.ts` :100-156 (`connect`/`_connect`), :157-186 (`openWs`), :215-217 (`isConnected`), :265-277 (`use`), :279-300 (`waitFor` overloads); `detectBrowsers`/`getBrowserCandidates`/`resolveWsUrl` module functions.

## Signature
```ts
// connect(): fast path isConnected → ride in-flight connectPromise → persist autoAllow
// _connect(opts): explicit {wsUrl|profileDir|port} → resolveWsUrl + openWs(timeoutMs ?? 5000);
//   else detectBrowsers() — "scans OS-specific profile dirs via detectBrowsers() and tries each
//   candidate (most-recently-launched first) until a WebSocket open succeeds. Each attempt has a
//   short timeout so dead ports and permission-denied (403) candidates fail fast."
//   Zero candidates ⇒ error listing scanned names; all-refused ⇒ error with per-candidate reasons.
// openWs: WS timeout timer; Dia-only macOS auto-Allow: if still CONNECTING past autoAllowDelayMs
//   (default 600ms), "fire one Return at the Dia process" (dismissDiaAllowPrompt), keep waiting;
//   close handler rejects pendings ONLY when this.ws === ws ("A parallel connect() can create a
//   phantom WS whose close handler would otherwise nuke pending entries belonging to the active WS").
```

## Data Shape
`use(targetId)` = Target.attachToTarget({flatten:true}) stored as activeSessionId; per-call sessionId args bypass it — every data skill uses the explicit-session form so parallel calls never share routing state.

## Decisive source
session.ts comments quoted above (:105-111, :157-166). waitFor docstring (:291-294): "If `sessionId` is given, only fires for events from that session — critical for avoiding cross-fire in parallel tab use" — the property the arm-before-navigate pattern depends on.

## Flow / Invariant
1. Auto-detect is ordered by recency and fail-fast per candidate; explicit opts skip detection entirely.
2. Single-flight connect prevents WS storms; cleared on failure so drops can reconnect.
3. Pending-call rejection is identity-guarded to the live socket.
4. Session-scoped event waits are the parallelism enabler.

## Probe (direct tests)
Executed at this pin: `node --experimental-strip-types --test session.test.ts` → 1 passed ("getBrowserCandidates includes Helium on every supported platform"). Live connect ladder exercised against Chromium/151 via `{port:9333}` explicit connect through the real daemon. Static probe: `grep -c "connectPromise" skills/cdp/sdk/session.ts` → 6 (:81 decl, :118 ride-on, :122 assign, :124 await, :126 clear-on-failure, :130 clear-on-success).

## Retrieve
`search_graph --project browser-harness-js --query "detectBrowsers"` / entry_points listing from index_status.

## Verdict
ADOPT the ladder wholesale for any CDP client; the phantom-WS guard is the subtlest invariant and the most commonly missed on reimplementation.
