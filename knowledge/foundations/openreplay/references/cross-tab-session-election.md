<!-- capsule-v2 -->
# RickRoll cross-tab BroadcastChannel election — how do same-origin tabs agree on ONE active session?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What protocol lets a second tab join the existing session (or fork it) without double-recording?

## Named message lines over `rick_<host>` channel
**Path/Symbol:** `tracker/tracker/src/main/app/index.ts` — `proto` map (:208–226: `ask`/`resp`/`reg`/`reset`/`polling`…), channel setup (:329–339), `bc.onmessage` (:407–453), reset fan-out (:1620–1625), frame pruning (:502–513).
**Signature:** `new BroadcastChannel('rick_' + host.replace(/\./g,'_'))`; messages `{line, source, context, projectKey, token?}`.
**Data Shape:** ask→resp/reg handshake; 250 ms startup grace timer; contextId guards self-echo; projectKey equality gate.

### Decisive source
```ts
if (ev.data.line === proto.ask) {
  const token = this.session.getSessionToken(this.projectKey)
  if (token && this.bc) {
    this.bc.postMessage({ line: ev.data.source === thisTab ? proto.reg : proto.resp,
                         token, source: thisTab, context: this.contextId, projectKey: this.projectKey })
  }
}
```

**Flow:** new tab broadcasts `ask` → incumbents reply `resp` (same token → both allowed) or the newcomer self-regenerates via `reg` when it sees its own source echoed; server-driven token rotation broadcasts `reset` forcing all tabs to restart with the fresh token. Child iframes use separate `polling` lines with a 1.5 s stale-frame prune.
**Invariant:** Messages whose `context === this.contextId` are ignored (self-echo); different `projectKey` messages are ignored entirely. Duplicate tabIds must be resolved to exactly one recorder — that's why `reg` regenerates the tabId before start.
**Probe:** `grep -c 'never-gonna-give-you-up' tracker/tracker/src/main/app/index.ts` → `2`; `grep -c "rick_" tracker/tracker/src/main/app/index.ts` → `1`; `grep -c 'pruneStaleFrames' tracker/tracker/src/main/app/index.ts` → `3`; direct test suite `tests/tabs.test.ts` covers TabChange side (executed green).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "ActivityState App allowAppStart BroadcastChannel tab election", limit: 10 });
```

## Verdict
Adopt the ask/resp/reg election. Adapt channel naming & timers. Omit iframe polling queue unless you port cross-domain frames.
