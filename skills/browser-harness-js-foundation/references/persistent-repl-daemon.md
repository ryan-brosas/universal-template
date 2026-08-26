<!-- capsule-v2 -->
# REPL daemon — how do you expose a stateful eval server whose snippets persist state across CLI invocations?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What makes `browser-harness-js '<js>'` feel like one continuous session across separate processes?

## Expression auto-return, empty-means-silent render, boot-cached version, delayed quit
**Path/Symbol:** `skills/cdp/sdk/repl.ts:runSnippet`/`isExpression` (:106-127), `renderResult` (:137-144), `VERSION` read-once (:24-28), `/quit` handler (:197-203); the launcher that feeds it is `skills/cdp/sdk/browser-harness-js` (`post_eval` splits body/status, `start_repl` polls `/health` 100×0.1s).
**Signature:** `runSnippet(code: string): Promise<unknown>` — expression form wraps as `(async () => { return (${code}); })()`, statement form passes through inside the same async wrapper; evaluated via indirect `(0, eval)`.
**Data Shape:** POST /eval body is RAW JS (not JSON); response 200 = rendered result text/plain, 500 = stack trace on stderr path of the launcher.

### Decisive source
```ts
function isExpression(code: string): boolean {
  const trimmed = code.trim();
  if (!trimmed) return false;
  if (/[;\n]/.test(trimmed)) return false;
  if (/^(let|const|var|if|for|while|do|switch|class|function|throw|try|return|import|export)\b/.test(trimmed)) return false;
  return true;
}
...
function renderResult(v: unknown): string {
  const s = serialize(v);
  if (s === undefined || s === null) return '';
  if (typeof s === 'string') return s;                    // bare text, no JSON quotes
  if (Array.isArray(s) && s.length === 0) return '';
  if (typeof s === 'object' && s !== null && Object.keys(s).length === 0) return '';
  return JSON.stringify(s);
}
```
and the stale-daemon seam:
```ts
// Read once at boot and cache for the process lifetime, so /health reports the
// version the daemon was *started* with — not the one currently on disk.
const VERSION = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')).version;
```

**Flow:** launcher `is_up` → spawn `node repl.ts` via nohup, poll `/health` up to 10s → POST raw code to /eval → daemon evaluates inside ONE long-lived process where `session`, the active sessionId, event subscribers and every `globalThis.<x>` a snippet set all survive → render by the table above (empty output for undefined/null/""/{}/[]) → errors go to stderr with exit 1. `/quit` answers `{ok:true}` FIRST and only then `setTimeout(...50ms)` closes server + session + exits, so the ack flushes.
**Invariant:** (1) multi-statement snippets DO NOT auto-return — the wrapper needs an explicit `return X` (the single-expression rewrite only applies when there's no `;`/newline and no statement keyword). (2) The version asymmetry IS the staleness detector: `--version` reads disk fresh each call; `/health.version` is boot-cached — lower/disk-missing means restart required. Bump package.json on every SDK change or installed copies can never know they're behind. (3) Globals persist because evaluation happens in the daemon process — env vars exported in the caller's shell deliberately DON'T reach it.
**Probe:** no direct test for repl.ts. Deterministic probes: `grep -n "isExpression\|return (" skills/cdp/sdk/repl.ts` (:106-127); launcher contract `grep -n "___STATUS___\|is_up && return" skills/cdp/sdk/browser-harness-js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "runSnippet", limit: 3, fields: ["signature", "name", "file"] });
// resolves repl.runSnippet @ repl.ts:123-127
```

## Verdict
Adopt the persistent-daemon + globalThis-state + expression/statement duality pattern for any CLI-driven stateful runtime; adapt the port/env surface (`CDP_REPL_PORT`, log path) to your tool; omit the recordings/video subcommands from your clone unless you also port their capsules. Caveat: HTTP-server behavior source-pinned; upstream tests cover none of repl.ts.
