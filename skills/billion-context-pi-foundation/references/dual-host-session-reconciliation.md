<!-- capsule-v2 -->
# Dual-host session-entry reconciliation — how does one adapter serve two hosts whose session logs lag differently?

**Source:** billion-context-pi (MIT) `master@1c87eb5051e0e97bb6ba606dc1c57ec2510f1b41`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** How do you rebuild a complete message context when the host's persisted log may not yet contain the messages about to be sent?

## Feature-detect the host, merge live messages only where the branch lags
**Path/Symbol:** `src/runtime.ts`: `readContextEntries` (:30-35), `isPiHost` (:37-40), `mergeLiveEntries` (:107-135), `stateFor` (:371-395).
**Signature:** `readContextEntries(sm) -> SessionEntry[]` via `sm.buildContextEntries?.() ?? sm.getBranch?.() ?? []`; `mergeLiveEntries(entries: SessionEntry[], live: AgentMessage[]) -> SessionEntry[]`.
**Data Shape:** unmatched tail messages get synthetic ids `live-<index>` with `parentId:null`; matched ones keep their PERSISTED entry object (stable id → kernel refs survive once the message is actually written next turn).

### Decisive source
```ts
// runtime.ts:377-384 (pass-4 pin) — why the merge exists at all
// omp fires the context event BEFORE the current user message is persisted
// to the session branch ... so getBranch() lags one message behind and the
// current prompt would be dropped from the rebuilt context.
// pi appends user messages to the session before the LLM call, so its
// buildContextEntries() is always current. Merge event.messages ... on the
// omp path only.
const merged = isPiHost(sm) || !liveMessages || liveMessages.length === 0
  ? entries
  : mergeLiveEntries(entries, liveMessages);
```

**Flow:** detect host by capability (`buildContextEntries` = pi; `getBranch` = omp) — never by name sniffing. On the lagging host, walk `live` in order and advance a cursor `p` over persisted entries matching on role then deep-content equality (`sameMessage`, JSON.stringify compare with try/catch falling back to identity); matched → reuse the persisted entry (STABLE id), unmatched → fabricate a `live-N` entry so the message still enters context this turn.
**Invariant:** matching must preserve persisted entry ids — a fresh id each turn would orphan every ref/tag pointing at that message. Equality failures degrade to reference equality, never throw. The whole merge is skipped on hosts whose log is already current.
**Probe:** `tests/integration.test.ts:113` ("omp context handler keeps the current (not-yet-persisted) user message"), `:149` ("omp live message keeps the same entry id once persisted").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "mergeLiveEntries readContextEntries isPiHost", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-detection over host sniffing plus stable-id-preserving live/persisted merge for any extension that must run under multiple agent hosts with different persistence timing. Adapt the exact accessor names to your host pair. Omit the JSON-equality fallback if your host guarantees content-stable ids.
