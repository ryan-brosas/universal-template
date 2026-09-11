<!-- capsule-v2 -->
# Node core-modules loader sentinel - how do you pre-prime a module cache before a debugger attaches to a child process?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How does an IDE force a Node child to warm its core-module cache BEFORE the inspector attaches, and sync on readiness?

## javascript-plugin helpers/node-core-modules/node-core-modules-loader.js
**Path/Symbol:** `plugins/javascript-plugin/helpers/node-core-modules/node-core-modules-loader.js` (whole file, 23 lines). Companion contract: nodeDebugInitializer forwarder (node-debug-connection-forwarder capsule) — this loader is the OTHER half of remote-attach preparation.
**Signature:** argv-driven: `node node-core-modules-loader.js <coreModuleNames...>`; readiness line: `@debugger: core modules loaded, ready for communication`; heartbeat every 1s, printed every 10th tick.
**Data Shape:** stdout protocol = one summary line + one machine-parsed sentinel + periodic `#N Waiting for external termination...` keepalives; failures go to stderr and are excluded from the summary.

### Decisive source
```js
var coreModuleNames = Array.prototype.slice.call(process.argv, 2);
coreModuleNames.forEach(function (coreModuleName) {
  try { require(coreModuleName); loadedCoreModuleNames.push(coreModuleName); }  // prime THIS process's cache
  catch (err) { console.error('Failed to load ' + coreModuleName, err); }
});
console.log('Loaded core modules: ' + loadedCoreModuleNames);
console.log('@debugger: core modules loaded, ready for communication');   // parent syncs on this line

var cnt = 0;
setInterval(function () { if (++cnt % 10 === 0)
  console.log("#" + cnt + " Waiting for external termination..."); }, 100); // never exits; killed externally
```

**Flow:** The IDE spawns plain `node` with this script so that `require()` of each named core module happens in the SAME process image the debugger will later attach to (module cache priming must precede inspector attachment to be visible). The parent blocks on reading the sentinel line from stdout — a fixed string, not a JSON envelope. Afterwards the process idles forever on a heartbeat; termination is purely external (kill), and the numbered keepalives let the parent distinguish a hung child from a dead one.
**Invariant:** sentinel is a literal string synced by the parent — no handshake library; per-module failure is non-fatal and reported out-of-band (stderr) so one bad name cannot stall attach; the helper deliberately never exits.
**Probe:** EXECUTED against shipped file (node v26.7.0): `node node-core-modules-loader.js fs path bogusmodule` → stdout exactly `Loaded core modules: fs,path` then `@debugger: core modules loaded, ready for communication`, stderr `Failed to load bogusmodule Error: Cannot find module 'bogusmodule'`; heartbeats `#10`/`#20` observed at ~1s cadence; exit=124 under timeout kill (never-exits confirmed).
**Coverage caveat:** file is indexed but has ZERO symbol-level graph nodes (top-level script, no functions) — search_graph file_pattern `*node-core-modules*` returns 0 rows; source read is the authority. check_index_coverage: no_recorded_issue @ gen 2026-08-24T13:57:05Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-phpstorm-light", paths: ["plugins/javascript-plugin/helpers/node-core-modules/node-core-modules-loader.js"] });
```

## Verdict
Adopt the prime-then-sentinel pattern whenever a debugger/profiler must observe a warmed process state. Adapt the primed set to your runtime's hot modules. Keep the sentinel a dumb literal and the failure path per-item. Omit the heartbeat only if your supervisor has another liveness channel.
