<!-- capsule-v2 -->
# Code-mode proxy bindings and source wrapping — how does sandboxed code call host tools it can't see?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does `tools.add({...})` inside the sandbox reach the right host function, including for names that aren't valid identifiers?

## Generated preamble + Proxy indirection
**Path/Symbol:** `packages/code-mode/src/run-code-mode.ts` — `createCodeModeSource` (:204–212, the single template literal at :211), `createHostFunctions` (:214–249), module counter `invocationCounter` (:60).
**Signature:** preamble = `const __codeModeBindings={name:__codeMode.toolN,...};const tools=new Proxy(Object.create(null),{get(_target,name){...}});const __codeModeResult=await(async()=>{<user js>})();if(__codeModeResult===undefined)return undefined;return JSON.parse(JSON.stringify(__codeModeResult));`
**Data Shape:** toolNames are SORTED (`Object.keys(input.tools).sort()`, :75) so index N in the binding map is stable across resume — a continuation's `__codeMode.tool2` must mean the same tool on replay.

### Decisive source
```js
get(_target,name){
  const binding=__codeModeBindings[name];
  return typeof binding==="function"
    ? (input)=>binding(input)
    : (input)=>__codeMode.missing(String(name),input);
}
```

**Flow:** every property read on `tools` resolves through the Proxy: known name → arity-1 wrapper around `toolN`; unknown name → `missing` fallback which STILL executes as a host round-trip (so the model gets a real "Unknown tool" error from the host, not a sandbox TypeError) — this is why `tools['lookup-user']` works (run-compatibility.test.ts:14–26). The user program is wrapped in an async IIFE inside the generated function, giving top-level `await`/`return`; the result is force-serialized with `JSON.parse(JSON.stringify(...))` unless `undefined`. Host side mirrors the naming: `group['tool'+index]` per sorted name plus one `group.missing`, all under namespace `__codeMode`.
**Invariant:** the sort-then-index mapping is the compatibility contract between first run and resumed run — re-sorting differently (or passing tools in a different order) invalidates every pending interruption id. The Proxy returns a FUNCTION for any property access (even `tools.foo.bar`), deferring all errors to the host boundary. `DIRECT_TOOL_CALL = 'AI_SDK_DIRECT_TOOL_CALL'` (`direct-tool-call.ts:6`) is a plain string precisely because it must survive JSON serialization across this bridge.
**Probe:** deterministic (repo root): `grep -n 'const tools=new Proxy' packages/code-mode/src/run-code-mode.ts` → `211:`; `grep -cF '__codeMode.missing' packages/code-mode/src/run-code-mode.ts` → `3` (template + two interruption decoders); `grep -n 'JSON.parse(JSON.stringify' packages/code-mode/src/run-code-mode.ts` → `211:`; direct test `run-compatibility.test.ts:17` calls `tools['lookup-user']`.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "createCodeModeTool experimental_toolCaller bind", limit: 3 });` // verified live @9d9a73f: rank#1 createCodeModeTool :20-46, rank#2 bind :57-58

## Verdict
Adopt sorted-name→indexed-host-function mapping plus catch-all Proxy with host-executed missing-tool path; adapt the namespace prefix if embedding elsewhere; omit the `run` package internals (external dep, versioned contract).
