<!-- capsule-v2 -->
# Cross-tab user-action recorder — how do you OBSERVE real user input when CDP's Input domain is send-only?

**Source:** browser-harness-js MIT `main@6b1904`→`main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the injection+binding architecture that records clicks/keys across every tab, including future ones?

## addBinding + addScriptToEvaluateOnNewDocument + setAutoAttach funnel into one sessionId-tagged stream
**Path/Symbol:** `skills/cdp/interaction-skills/record-cross-tab.md` (:1-182); primitives `session.onEvent` (session.ts :285-290), `Runtime.addBinding`, `Target.setAutoAttach`.
**Signature:** recipe: per-target `addBinding({name:'__rec'})` + listener injection; browser-level `setAutoAttach({autoAttach:true, waitForDebuggerOnStart:false, flatten:true})`; event funnels `Runtime.bindingCalled`, `Target.attachedToTarget`, `targetInfoChanged`, `detachedFromTarget`.
**Data Shape:** page side emits `window.__rec(JSON.stringify({ts,type,target:{tag,id,role,label,text,selector,value},extra}))` — password fields masked (`value:'***'`, `key` dropped); node side tags each record with the originating tab URL.

### Decisive source
```js
await session.Target.setDiscoverTargets({ discover: true })
await session.Target.setAutoAttach({ autoAttach: true, waitForDebuggerOnStart: false, flatten: true })
// on Target.attachedToTarget: instrument(sid) — Runtime.enable → addBinding →
// addScriptToEvaluateOnNewDocument(listener) → evaluate(listener) for the live doc,
// all with setActiveSession(sid) saved/restored around it and bursts run through an enqueue() promise chain.
```
Traps that ARE the contract:
- `Input.*` is send-only — CDP emits no "user clicked" event; that absence is WHY this exists.
- bindings + new-document scripts are PER-TARGET but SURVIVE reloads within the target.
- `waitForDebuggerOnStart: true` would freeze every new tab awaiting `Runtime.runIfWaitingForDebugger`.
- OOPIFs are separate targets NOT auto-instrumented by the page-level pass.

**Flow:** subscribe once (server keeps your closures across CLI calls until `off()` or restart) → attach existing + future pages → instrument each inside a pointer-saving serialized queue → listener captures click/change/submit/keydown capture-phase passive → binding payload JSON crosses to the daemon tagged by sessionId → read `globalThis.rec` from any later call.
**Invariant:** (1) Binding must exist BEFORE the first listener fire — inject order is addBinding THEN scripts. (2) Never block tabs (`waitForDebuggerOnStart:false`). (3) Keystrokes are recorded verbatim except password fields — remove the keydown hook unless you need keys. (4) Concurrent instrumentations must serialize or they interleave active-pointer mutations.
**Probe:** no test (needs a human browsing). Deterministic probe: full runnable recipe in docs matches SDK primitives 1:1 — `grep -n "setAutoAttach\|addBinding" skills/cdp/interaction-skills/record-cross-tab.md`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "onEvent", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt binding+auto-attach instrumentation whenever an agent must watch rather than drive; adapt the descriptor shape to what you downstream-parse; omit the keystroke channel for privacy-sensitive deployments (the doc says exactly which lines to drop).
