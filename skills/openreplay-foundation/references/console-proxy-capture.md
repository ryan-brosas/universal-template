<!-- capsule-v2 -->
# Console capture via Proxy + throttling — how do you record console output with format-string expansion and rate limits?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What patching mechanism and formatting rules must a console recorder copy?

## Reflect.apply passthrough, printf expansion, n-th tick reset
**Path/Symbol:** `tracker/tracker/src/main/modules/console.ts` — `printf` + printers (:10–89), method list (:96: log/info/warn/error/debug/assert), options (:98–105: `consoleThrottling: 30`), Proxy handler (:126–148), ticker reset `attach(reset, 33, false)` (:124).
**Signature:** `patchConsole(console, ctx)`; handler `apply(target, thisArg, argumentsList)`.
**Data Shape:** `%o %s %f %d %i` specifiers; objects truncated to 10 keys, arrays to 10 items (`Array(n)[a, b]`); Firefox error printing joins message+stack.

### Decisive source
```ts
apply: function (target, thisArg, argumentsList) {
  Reflect.apply(target, ctx, argumentsList)   // always pass through first
  n = n + 1
  if (n > options.consoleThrottling) return   // drop AFTER executing original
  sendConsoleLog(target.name, argumentsList)
}
```
```ts
// Firefox stack handling
const printError = 'InstallTrigger' in window
  ? (e) => e.message + '\n' + e.stack : (e) => e.stack || e.message
```

**Flow:** per context patch each enabled method with a Proxy → original runs unconditionally → counter increments → over-throttle messages are silently dropped; counter resets every ~1 s (33 ticks × 30 ms). privateMode replaces the formatted string with stars before send.
**Invariant:** The original console call MUST execute even when the capture is dropped (debugging output is never suppressed). Unsupported method names warn and skip rather than throw.
**Probe:** `grep -c 'consoleThrottling: 30' tracker/tracker/src/main/modules/console.ts` → `1`; `grep -c 'new Proxy(fn, handler)' tracker/tracker/src/main/modules/console.ts` → `1`; `grep -c "'InstallTrigger' in window" tracker/tracker/src/main/modules/console.ts` → `1`; direct tests `tests/console.test.ts` executed green.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "console Proxy apply printf throttling", limit: 10 });
```

## Verdict
Adopt passthrough-then-count. Adapt throttle budget. Omit printf expansion if you ship raw args.
