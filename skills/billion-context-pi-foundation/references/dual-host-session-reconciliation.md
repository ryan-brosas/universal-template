<!-- capsule-v2 -->
# Dual-host session-entry reconciliation — how does one adapter serve two hosts whose session logs lag differently?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How do you rebuild a complete message context when the host's persisted log may not yet contain the messages about to be sent?

## Feature-detect the host, merge live messages only where the branch lags
**Path/Symbol:** `src/runtime.ts`: `readContextEntries` (:30-35), `isPiHost` (:37-40), `mergeLiveEntries` (:107-135) over `messageIdentity` (`src/messages.ts`:121-123) and `findUniqueLongestRun` (`src/sequence-match.ts`:7-70), `stateFor` (:371-395).
**Signature:** `readContextEntries(sm) -> SessionEntry[]` via `sm.buildContextEntries?.() ?? sm.getBranch?.() ?? []`; `mergeLiveEntries(entries: SessionEntry[], live: AgentMessage[], state: CompressionState, origins: LiveRefOrigin[]) -> SessionEntry[]`.
**Data Shape:** unmatched tail messages get collision-checked synthetic ids `live-<index>` (`nextLiveId` :138-143 consults both usedIds and `state.messageRefs.byRaw`) with `parentId:null`; matched ones keep their PERSISTED entry object (stable id → kernel refs survive once the message is actually written next turn). Prior-turn `live-*` identities persist in session state as `LiveRefOrigin`s (`store.get/setLiveRefOrigins`, stateFor :386-388) so a tail message keeps ONE id across turns until persistence catches up.

### Decisive source
```ts
// runtime.ts:377-391 (current pin) — why the merge exists at all, omp path only:
// "omp fires the context event BEFORE the current user message is persisted
//  to the session branch ... so getBranch() lags one message behind and the
//  current prompt would be dropped from the rebuilt context. pi appends user
//  messages to the session before the LLM call, so its buildContextEntries()
//  is always current."
if (!isPiHost(sm) && liveMessages && liveMessages.length > 0) {
  const origins = store.getLiveRefOrigins(sessionFile, sessionId);
  const merged = mergeLiveEntries(entries, liveMessages, state, origins);
  store.setLiveRefOrigins(sessionFile, sessionId, origins);
  const coreMessages = entriesToCoreMessages(merged);
  return { state, coreMessages, entries: merged };
}
// pi path (:392-394): entries only; when liveMessages === undefined,
// pruneOrphanRefs drops messageRefs no longer retained by any projection id.
```

**Flow:** detect host by capability (`buildContextEntries` = pi; `getBranch` = omp) — never by name sniffing. On the lagging host, align persisted vs live lists by unique-longest-run over canonical identity strings: each side maps through `messageIdentity` (JSON with timestamps dropped, keys sorted, tag-only text blocks removed — tags must not change who a message IS); a first matcher matches persisted entries into the live list (repeated toolResults disambiguated by `toolName\0toolCallId` structure key via `normalizePersistedMatchKeys` :171-192 — duplicated candidates become a NO_PERSISTED_MATCH symbol = deliberately unmatchable, unique ones verified by `sameToolResult` = same non-text blocks + truncation-marker-aware `matchesStoredText`); a second matcher matches prior-turn ORIGIN records into the live list. A live position inside either match range adopts that source's STABLE id (migrating refs off the old `live-N` placeholder via `migrateLiveRefs`/`migrateTaggedRef` :121-122/:145-165, `${id}#call` splits included); positions in neither range fabricate a fresh `live-N` entry so the message still enters context this turn.
**Invariant:** matching must preserve persisted entry ids — a fresh id each turn would orphan every ref/tag pointing at that message. Alignment refuses ambiguity anywhere (`findUniqueLongestRun` returns undefined for BOTH no-match and ambiguous-match; callers treat undefined as NO MATCH). Equality checks never throw (JSON compare guarded; symbol keys mark unmatchables). The whole merge is skipped on hosts whose log is already current, and orphaned refs are pruned on the pi path.
**Probe:** `tests/integration.test.ts:130` ("omp context handler keeps the current (not-yet-persisted) user message"), `:167` ("omp live message keeps the same entry id once persisted").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "mergeLiveEntries readContextEntries isPiHost", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-detection over host sniffing plus stable-id-preserving live/persisted alignment for any extension that must run under multiple agent hosts with different persistence timing — align by canonical content identity through a uniqueness-refusing matcher, and persist prior-turn synthetic ids so a tail message keeps one id until the log catches up. Adapt the exact accessor names to your host pair. Omit the truncation-aware tool-result matching if your host never mutates bodies after storage.
