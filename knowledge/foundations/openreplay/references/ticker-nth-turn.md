<!-- capsule-v2 -->
# Ticker n-th turn scheduler — how do 30 ms capture cycles share one timer without starving?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** How should modules piggyback on a single interval with per-module skip counts?

## unshift + wrap(callback, n) modulo trick
**Path/Symbol:** `tracker/tracker/src/main/app/ticker.ts` — whole file (:1–55): `wrap` (:4–12), `Ticker.attach(callback, n, useSafe, thisArg)` (:27–35), `start/stop` 30 ms setInterval (:37–54).
**Signature:** `attach(cb: () => void, n = 0, useSafe = true): void`.
**Data Shape:** callbacks array; each entry either raw or wrapped with counter `t`; interval 30 ms.

### Decisive source
```ts
function wrap(callback: Callback, n: number): Callback {
  let t = 0
  return (): void => {
    if (t++ >= n) { t = 0; callback() }
  }
}
...
// note the intentional expression-statement quirk: unshift(...) - 1
this.callbacks.unshift(n ? wrap(callback, n) : callback) - 1
```

**Flow:** modules attach with skip factors — input value polling `n=3` (~90 ms), scroll flush `n=5`, viewport size `n=5`, console throttle reset `n=33` (~1 s), commit every tick. All run inside one interval; `app.safe()` wraps user-facing callbacks so a throw can't kill the cycle.
**Invariant:** Skip counting is `t++ >= n` (fires on the (n+1)-th tick) — off-by-one vs naive `%n`. The trailing `- 1` after unshift is dead arithmetic kept for history; a porter must not "fix" it into an argument.
**Probe:** `grep -c 'unshift(n ? wrap(callback, n) : callback) - 1' tracker/tracker/src/main/app/ticker.ts` → `1`; `grep -c '}, 3)' tracker/tracker/src/main/modules/input.ts` → `1`; direct test: none upstream for ticker itself (grep-pinned); consumers verified via full jest suite.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "Ticker attach wrap interval callbacks", limit: 10 });
```

## Verdict
Adopt single-timer multiplexing. Adapt intervals. Omit safe-wrapper if your host catches globally.
