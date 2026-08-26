<!-- capsule-v2 -->
# WebConsole JSBridge callback registry - how does an embedded browser page call back into the JVM without leaking closures?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** What is the smallest safe bridge contract between a JCEF page and its host process?

## webConsole interop.js
**Path/Symbol:** `plugins/javascript-debugger/webConsole/interop.js:callJVM` (:33-42) + `window.callback` (:44-50) + `processRequests` (:54-61); companion `WebConsole.instance()` at `WebConsole.js:201-205`.
**Signature:** `callJVM(funcName, args, callback?, preserveCallback?): callbackId`; host reentry: `window.callback(callbackId, args)`; inbound batch: `processRequests(batch)` where request = `{first: methodName, second: args[]}` (Kotlin Pair encoding).
**Data Shape:** `callbackMap: Map<id, {preserve, callback}>`; ids from a counter mod 10000; Printable objects carry id/type(text|tree|tree-link|message-link|message-tree-node)/text[]/styleClasses/deferred+deferredID/iconURL.

### Decisive source
```js
function callJVM(funcName, args, callback, preserveCallback) {
  if (callback != null) {
    callbackMap.set(callbackCounter, {preserve: preserveCallback, callback});
    args.push(callbackCounter++); callbackCounter = (callbackCounter + 1) % 10000;
  }
  window.JSBridge[funcName](...args);
}
window.callback = function (callbackId, args) {
  let e = callbackMap.get(callbackId); e.callback(args); if (!e.preserve) callbackMap.delete(callbackId);
};
```

**Flow:** JS→JVM: append the registered id as the LAST positional argument, then invoke the injected JSBridge function; JVM→JS: host looks up the id, invokes once, deletes unless preserve (streaming/progress callbacks replay forever). JVM pushes work in batches through processRequests which dispatches method-name + spread args onto the WebConsole singleton. In-source fixme admits long-running tasks freeze the browser thread — heavy work belongs host-side.
**Invariant:** the callback id rides IN the argument list (positional protocol, no envelopes); one-shot vs persistent is explicit at registration; bounded id space (mod 10000) relies on delete-on-fire to stay collision-free.
**Probe:** executed against shipped file in a window sandbox: sequential ids 0,1 appended as final args (["hello",0],["persist",1]); window.callback(0) fired once and deleted; preserve entry fired twice on repeated callbacks ("two","two").
**Coverage caveat:** coverage no_recorded_issue; graph line-exact (interop.callJVM :33-42, WebConsole.instance :201-205).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "callJVM JSBridge printable WebConsole instance", limit: 6 });
```

## Verdict
Adopt id-mapped callbacks with explicit persistence for ANY single-process injected bridge (JCEF, WebView2, Electron preload). Adapt the transport name (JSBridge is convention). Omit batching only if your host serializes per-call anyway — but keep the fixme lesson: never run long tasks on the UI page thread.
