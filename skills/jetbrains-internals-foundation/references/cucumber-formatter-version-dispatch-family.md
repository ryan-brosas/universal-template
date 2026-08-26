<!-- capsule-v2 -->
# Cucumber formatter three-generation adapter family — how does one reporter codebase absorb three breaking cucumber-js event APIs?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (proprietary distribution; study/reference use only); Codebase Memory `jetbrains-webstorm`. **Question:** above.

## The dispatch is a file-per-generation family, not an in-file branch
**Path/Symbol:** `plugins/javascript-cucumber/lib/cucumberjs_formatter.js` (entry, :1-10), `cucumberjs_formatter_v2.js` (:1-14), `cucumberjs_formatter_v3.js` (:1-146), `cucumberjs_formatter_v7.js` (:3-39).
**Signature:** entry: `module.exports = function () { for (var key in ourHandlers) this[key](ourHandlers[key]) }`; adapters: `function (options)`.
**Data Shape:** every adapter receives the host-provided `options` carrying `cucumberLibPath` (v7 nests it under `parsedArgvOptions`) — each adapter then does `require(options.cucumberLibPath)` to load the USER'S cucumber, never a bundled copy.

### Decisive source
```js
// cucumberjs_formatter.js — v1-style: register named handlers onto the formatter object
var ourHandlers = common.buildHandlers(false)
module.exports = function () {
  for (var key in ourHandlers) {
    if (ourHandlers.hasOwnProperty(key)) this[key](ourHandlers[key])
  }
}

// cucumberjs_formatter_v7.js:13-35 — newest generation: ONE envelope listener, demux by envelope key
options.eventBroadcaster.on('envelope', function (envelope) {
  if (envelope.testCase) { logTestCase(envelope.testCase) }
  else if (envelope.testRunStarted) { logTestRunStarted() }
  ...
})
```

**Flow:** JVM-side run configuration (inside javascript-cucumber.jar — jar internals are NOT symbol-indexed; standing coverage caveat) detects the project's cucumber-js major → selects exactly one of the four loose files as the formatter module → passes `cucumberLibPath`; the adapter binds itself to whichever registration style that major supports.
**Invariant:** the adapter never bundles or version-checks cucumber itself; it requires the user's cucumber by explicit path and adapts to ITS event shapes. Breaking upstream API changes produce a NEW FILE, not a compatibility shim inside the old one.
**Probe:** no upstream tests ship with the installed distribution. Executed live: `node -e 'const f=require(".../cucumberjs_formatter.js"); const sink={}; for (const k of ["BeforeFeatures","BeforeFeature","BeforeScenario","BeforeStep","StepResult","AfterScenario","AfterFeature","AfterFeatures"]) sink[k]=h=>registered.push(k); f.call(sink)'` → 8 handlers registered by key iteration. Plus `node --check` GREEN ×5 on all family files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", file_pattern: "plugins/javascript-cucumber/*", limit: 80 });
// total: 63 rows — the whole subsystem; entry module + _common + v2/v3/v7 adapters, nothing else loose
```

## Verdict
Adopt the file-per-breaking-major adapter family with a host-injected `cucumberLibPath` (keeps reporter code shippable across ecosystems you don't control). Adapt the selection mechanism to your host's own detection point. Omit nothing structural here — but note `buildHandlers` has exactly two callers (v1 entry + v2; confirmed via trace_path inbound), so the common handler set is dead weight for v3/v7 consumers.
