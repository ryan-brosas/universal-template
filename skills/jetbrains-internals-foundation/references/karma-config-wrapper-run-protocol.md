<!-- capsule-v2 -->
# Karma server-hijack bridge - how does an IDE own a Karma run (config, reruns, debugging) without forking Karma?

**Source:** PhpStorm installed build PS-262.9437.196 (plugins/karma/js_reporter/karma-intellij/, 19 files ~1.9k LOC); Codebase Memory project jetbrains-phpstorm. **Question:** Port an IDE runner integration for a test server you cannot modify: which seams give you config control, incremental reruns, and breakpoint-proof debugging?

## Wrapper config + rerun protocol
**Path/Symbol:** lib/intellij.conf.js (whole 181L wrapper), lib/karma-intellij-parameters.js (PREFIX '_INTELLIJ_KARMA_INTERNAL_PARAMETER_'), lib/intellijCli.js (--key=value args), lib/intellijRunner.js:33-71 (POST urlRoot+/run), :8,:14-31 (EXIT_CODE_BUF 0x1F EXIT trailer strip), :91-99 ('resume-test-running' stdin handshake), lib/fakePlugin.js (empty exports vs karma-* wildcard), lib/ng-template.js (Angular-template built-in config), lib/karma-intellij-debug.js (timeout ladder + context.html splice + browser launcher synthesis), static/delay-karma-start-in-debug-mode.js (window.__karma__ Proxy, 500ms).
**Data Shape:** rerun body JSON {args:['--testNamePattern_intellij=...'], removedFiles, changedFiles, addedFiles, refresh}. Response frames end with byte 0x1F + 'EXIT' (+2 bytes) stripped before stdout echo. Params via env PREFIX+name; user_config REQUIRED (throws), debug/coverage_temp_dir optional.

### Decisive source
```js
function disableSingleRun(config) {
  config.singleRun = false;
  const prevSet = config.set;
  // Workaround if karma server is instantiated with { singleRun: true }
  // For example, @angular/cli is the case:
  if (typeof prevSet === 'function') { config.set = function (nc) { if (nc.singleRun === true) nc.singleRun = false; prevSet.apply(config, arguments); }; }
}
// intellijRunner: POST {urlRoot}/run, stream response, strip exit-code trailer
var EXIT_CODE_BUF = Buffer.from('\x1FEXIT');
```

**Flow:** IDE spawns karma with the WRAPPER config; the USER config path arrives via prefixed env. The wrapper requires the user config as a module and mutates the SAME object: ESM .default interop; promise-returning configs awaited (sync path kept for old Karma, WEB-73699 cited inline); karma.conf.ts compiled by ts-node required FROM PROJECT ROOT via module.createRequire(cwd + sep). It strips dots/progress reporters, appends its reporter, excludes the original config path from browser loading, forces LOG_INFO (Karma bug 614 cited), kills autoWatch/batchDelay (IDE drives reruns), resolves basePath exactly like Karma does relative to the user config dir, and finally emits a configFile snapshot event. singleRun is forced false INCLUDING intercepting config.set so Angular CLI cannot flip it back. fakePlugin.js sits NEAR karma exporting {} purely to neutralize karma's karma-* wildcard auto-load double-registering the real explicitly-pushed plugin. No-user-config projects get ng-template.js mirroring the Angular CLI karma.conf template (createRequire(workspaceRoot) plugin resolution; ChromeHeadlessNoSandbox launcher; drops devkit plugin pair when env _JETBRAINS_RUN_WITH_NG_UNIT_TEST_BUILDER_=true).
**Invariant (debug suspension policy):** EVERY watchdog a suspended debugger would trip gets neutralized together: browserNoActivityTimeout=null, pingTimeout=24h constant, injector-resolved webServer.timeout=0 installed on nextTick (breaks webServer-reporter circular dep, comment says so), socketServer heartbeat timeout/interval=24h (pre-karma6 path), client.mocha.timeout=0. context.html is patched by STRING-SPLICE after the %MAPPINGS% placeholder into a mkdtemp copy set as customContextFile (fail-open console.error); the injected Proxy defers karma.start() 500ms so the debugger attaches. Browsers: Chrome/Canary/Chromium synthesized into customLaunchers['_INTELLIJ_KARMA_DEBUG_'+name] with --remote-debugging-port=9222; Headless variants count as preconfigured; effective port echoed via the configFile debugInfo event.
**Probe:** executed this run: node --check green on ALL lib/*.js, lib/kjhtml/*.js, static/*.js (node v26.7.0); MCP symbol retrieval confirms sendIntellijEvent at intellijUtil.js:112-114 and attributeValueEscape at :46-63.
**Coverage caveat:** helpers have no shipped test suite in the install; probes are syntax + graph-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-phpstorm", qualified_name: "jetbrains-phpstorm.plugins.karma.js_reporter.karma-intellij.lib.intellijUtil.sendIntellijEvent" });
```

## Verdict
Adopt wrap-mutate-reemit over forking: require the user's config as a module, mutate one object, keep a sync fallback. Adapt the param-prefix and rerun verbs. Omit watcher-driven rerun modes if your IDE needs test-name filtering - the POST /run protocol is what makes filtered reruns deterministic.