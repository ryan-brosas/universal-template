<!-- capsule-v2 -->
# Bridge init bootstrap boundary — title derivation policy and bundle-isolation dependency injection

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you keep a daemon-importable core free of the CLI/React tree while the REPL wrapper owns gates, git context, and session titles?

## Path/Symbol
**Path/Symbol:** `src/bridge/initReplBridge.ts` — whole file: gate ladder (:134-241), v1/v2 fork with naming doc (:397-452), title precedence (:247-300), count-1/count-3 onUserMessage policy (:302-378) incl. genSeq out-of-order guard (:333-348) and env-lost reset (:353-363), `deriveTitle` first-sentence regex (:547-569); injection rationale docstrings in `src/bridge/replBridge.ts` BridgeCoreParams (:99-221: createSession/toSDKMessages/onAuth401/getPollIntervalConfig each name its transitive ~1300-module chain).
**Signature:** `initReplBridge(options?) → ReplBridgeHandle | null`; `onUserMessage(text, sessionId): boolean` — returns true to stop further calls.
**Data Shape:** title flags: `hasExplicitTitle` (initialName//rename — never auto-overwritten) vs `hasTitle` (any title — blocks count-1 but not count-3).

### Decisive source
```ts
// Split out of replBridge.ts because the sessionStorage import
// (getCurrentSessionTitle) transitively pulls in src/commands.ts → the
// entire slash command + React component tree (~1300 modules). Keeping
// initBridgeCore in a file that doesn't touch sessionStorage lets
// daemonBridge.ts import the core without bloating the Agent SDK bundle.
...
// same-session out-of-order resolution (genSeq — count-1's Haiku resolving
// after count-3 would clobber the richer title)
const gen = ++genSeq
void generateSessionTitle(input, AbortSignal.timeout(15_000)).then(generated => {
  if (generated && gen === genSeq && lastBridgeSessionId === bridgeSessionId &&
      !getCurrentSessionTitle(getSessionId())) { patch(generated, ...) }
})
```

**Flow:** wrapper reads ALL bootstrap state (gates, cwd, OAuth, branch, orgUUID, titles) then hands explicit params to the bootstrap-free core — the daemon fills them itself. Title pipeline: slug fallback (`remote-control-graceful-unicorn`) → placeholder at first prompt (strip display-tags, first sentence via capture-group regex "keeps YARR JIT happy", 50-char ellipsis) → async Haiku regeneration fire-and-forget → re-derive at 3rd prompt over post-compact-boundary conversation. Guards: explicit titles latch off; /rename re-checked at call time; generation sequence number discards stale resolutions; v1 env-loss resets the counter for the new session while keeping hasTitle.

**Invariant:** (1) The heavy-tree imports live ONLY in the wrapper layer; anything the core needs from them arrives as an injected callback. (2) Async title writes need THREE guards — generation seq, session-ID match, and a fresh /rename check — or slow resolutions clobber newer state. (3) The v2 flag gates ENV-LESS (no poll loop), NOT transport version; the env-based path can also run CCR v2 transport — conflating the two names breaks rollout reasoning. (4) perpetual mode is env-coupled and deliberately falls back to v1.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "~1300 modules" src/bridge/initReplBridge.ts` (:119) and `src/bridge/replBridge.ts` (:153); `grep -n "keeps YARR JIT happy" src/bridge/initReplBridge.ts` (:561); `grep -n "tengu_bridge_repl_v2 gates env-less" src/bridge/initReplBridge.ts` (:404-405); graph resolves `locoagent.src.bridge.initReplBridge.initReplBridge` :110-545 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "initReplBridge deriveTitle generateAndPatch BridgeCoreParams previouslyFlushedUUIDs", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the wrapper/core split as the canonical SDK-bundle-isolation pattern; adopt the three-guard async-title policy for any LLM-derived metadata. Adapt title sources/prompt; omit KAIROS assistant-mode plumbing if absent.
