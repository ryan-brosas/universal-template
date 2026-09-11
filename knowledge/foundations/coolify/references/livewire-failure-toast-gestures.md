<!-- capsule-v2 -->
# Infrastructure failure toast: gesture-window classification + per-gesture dedupe

## Source
Coolify `main@98116397`, `resources/js/livewire-request-failure.js` (whole file, 68L). Drift-introduced plane (upstream commit `c1219576`); direct test `resources/js/livewire-request-failure.test.js` (146L, RUNNER EXECUTED: `node --test` = 9/9 pass at pin).

## Question
How do you surface a user-facing toast ONLY for gateway-level failures (Cloudflare 52x/502/503/504), exactly once per user action, while background polling stays silent?

## Path / Symbol
`createLivewireRequestFailureHandler({ now })` :13-44; `registerLivewireRequestFailureHandler(Livewire, documentObject, { now })` :47-68; constants `INFRASTRUCTURE_FAILURE_STATUSES`, `GESTURE_WINDOW_MS = 2_000`, `WARN_COOLDOWN_MS = 10_000`, `USER_GESTURE_EVENTS`.

## Signature
```js
export const INFRASTRUCTURE_FAILURE_STATUSES = new Set([502,503,504,520,...,530]);
export const GESTURE_WINDOW_MS = 2_000;
createLivewireRequestFailureHandler({ now = Date.now } = {})
  → ({ status, content, preventDefault, gestureAt = -Infinity }) => void
registerLivewireRequestFailureHandler(Livewire, documentObject = document, { now })
  // captures trusted gestures (click/submit/keydown/input/change) capture-phase,
  // classifies at REQUEST SEND time, wires Livewire.hook('request') fail callback.
```

## Data Shape
Gesture bookkeeping: `lastGestureAt` timestamp updated only for `event.isTrusted`; per-request `gestureAt = (now - lastGestureAt <= GESTURE_WINDOW_MS) ? lastGestureAt : -Infinity`. Handler state: `lastWarnAt`, `lastToastGestureAt` (both start at `-Infinity`).

## Decisive source
```js
Livewire.hook('request', ({ fail }) => {
    // Classify at send time: infrastructure failures (522/524) can arrive
    // long after the gesture, so the failure timestamp is meaningless.
    const gestureAt = now() - lastGestureAt <= GESTURE_WINDOW_MS ? lastGestureAt : Number.NEGATIVE_INFINITY;
    fail((failure) => handleFailure({ ...failure, gestureAt }));
});
...
if (gestureAt > lastToastGestureAt) {          // one toast PER GESTURE, not per request
    lastToastGestureAt = gestureAt;
    window.toast?.('Action could not be completed', { type: 'danger', description: ... });
}
```

## Flow / Invariant
INVARIANTS (each test-pinned):
1. **Classify at SEND time, not failure time** — a 522 can arrive minutes after the click; comparing timestamps AT FAILURE would misclassify. The comment in-source documents this as contract.
2. **Strict `>` on gesture identity** — one click failing N component requests toasts ONCE (all carry the same gestureAt); a retry is a NEW gesture (larger timestamp) and always toasts again; background requests carry `-Infinity` and NEVER toast.
3. **preventDefault() runs for EVERY infrastructure status** regardless of toast gating — Livewire's default error modal must always be suppressed for these codes; non-infra statuses return early WITHOUT preventing (default handling preserved).
4. Console diagnostics are separate from UX: throttled to one per 10s and content truncated to 2000 chars.
5. Untrusted synthetic events never count as gestures (`isTrusted` gate) — programmatic dispatch can't manufacture toasts.
6. Missing `window.toast` degrades silently (`window.toast?.`).

## Probe (direct tests)
From repo root (real runner):
```bash
node --test resources/js/livewire-request-failure.test.js 2>&1 | grep -E '^ℹ (tests|pass|fail)'
```
Expect `tests 9 / pass 9 / fail 0` (EXECUTED GREEN at pin). Static anchors:
```bash
grep -c 'GESTURE_WINDOW_MS = 2_000' resources/js/livewire-request-failure.js
grep -c 'gestureAt > lastToastGestureAt' resources/js/livewire-request-failure.js
```
Expect 1 / 1.

## Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-coolify","query":"createLivewireRequestFailureHandler gesture","limit":3}'
```
→ rank-1 `Function resources/js/livewire-request-failure.js 13-44`.

## Verdict
ADOPT verbatim (dependency-free ES module; swap the Livewire hook for your fetch/XHR failure funnel, keep the send-time classification + strict-> per-gesture latch).
