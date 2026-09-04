<!-- capsule-v2 -->
# Node debug connection forwarder - how do you attach a debugger across a host boundary without losing initial breakpoints?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** What is the minimal reliable relay between an inspector port inside a sandbox and a debug gateway outside it?

## nodeDebugInitializer plane
**Path/Symbol:** `plugins/javascript-debugger/nodeDebugInitializer/debugConnectionForwarder.js:forwardDebugConnection` (:5-27); `debugConnectorUtil.js:getGatewayHostPort/forwardDebugConnectionAndWait` (:1-31).
**Signature:** CLI child: `node debugConnectionForwarder.js <debugPort>`; env: `JB_NODE_DEBUG_CONNECTION_GATEWAY_HOST/PORT`; verbose gate `JETBRAINS_NODE_DEBUGGER_VERBOSE_LOGGING`.
**Data Shape:** pure TCP byte relay — two net sockets cross-`pipe()`d with `setNoDelay(true)`; no protocol awareness.

### Decisive source
```js
spawn(process.execPath, [require.resolve('./debugConnectionForwarder.js'), debugPort], {
  env: Object.assign({}, process.env, { NODE_OPTIONS: '' }),   // scrub inherited inspect flags!
  stdio: 'inherit', windowsHide: true });
if (typeof inspector.waitForDebugger === 'function') inspector.waitForDebugger();   // v12.7.0 guard
else console.error('... Some initial breakpoints might be skipped.');
```

**Flow:** parent (the debugged app process) spawns the forwarder child with NODE_OPTIONS emptied so --inspect flags don't recurse into the helper; child validates argv port (non-numeric → stderr message naming argv, exit 1), resolves gateway from env (missing/unparsable → null → exit 1), connects both ends, pipes gateway→inspector and inspector→gateway; parent then calls inspector.waitForDebugger() so V8 holds the app until the IDE registers breakpoints and issues Runtime.runIfWaitingForDebugger. Verbose mode tags every socket event with `[caller pid:P, ppid:PP]` bracket messages.
**Invariant:** the relay must stay protocol-blind (CDP frames pass through untouched); breakpoint sync depends on BOTH the NODE_OPTIONS scrub and the waitForDebugger handshake — dropping either loses initial breakpoints or forks infinite helpers.
**Probe:** executed: getGatewayHostPort parses {host,port} / returns null when PORT missing; forwarder with argv "notaport" printed `[debugConnectionForwarder] debug port expected, argv=[...]` and EXIT=1; verbose formatMessage observed to embed pid/ppid INSIDE the bracket tag.
**Coverage caveat:** coverage no_recorded_issue ×2 (+webConsole sibling file checked separately); no shipped tests.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "forwardDebugConnection gateway host port", limit: 6 });
```

## Verdict
Adopt the blind TCP relay + env-scoped config + NODE_OPTIONS scrub as the standard remote-debug attach ladder. Adapt gateway discovery to your host (env today, file-based tomorrow). Keep the waitForDebugger capability guard — old runtimes degrade to best-effort breakpoints WITH a logged warning, never silently.
