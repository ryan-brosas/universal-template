<!-- capsule-v2 -->
# Discord thread context persistence — how do you persist per-thread participant identity without ever disturbing the bound session?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** Multiple humans may speak in one Discord thread — how do you record WHO is currently speaking while keeping the thread's RPC session identity stable?

## Normalized-author-first identity with eight-slot raw fallback and no-op-skip writes
**Path/Symbol:** `apps/cli/src/connectors/adapters/discord.ts:resolveDiscordParticipant` (:219-246) + `persistDiscordThreadContext` (:580-617).
**Signature:** `persistDiscordThreadContext(input: { thread; bindingsPath; baseStartRequest; message: { raw; author }; errorLabel }): Promise<DiscordParticipant | undefined>`.
**Data Shape:** In: the chat-SDK message (normalized author + raw platform payload), the bindings file path. Out: the resolved participant (or undefined), with thread state merged into the binding store.

### Decisive source
```ts
const normalized = resolveDiscordParticipantFromAuthor(messageAuthor);
if (normalized) return normalized;          // adapter-normalized author WINS
const candidates = [
    asRecord(raw?.author), asRecord(asRecord(raw?.member)?.user), asRecord(raw?.user),
    asRecord(data?.author), asRecord(asRecord(data?.member)?.user), asRecord(data?.user),
    asRecord(asRecord(raw?.message)?.author), asRecord(asRecord(data?.message)?.author),
];
// ... first candidate yielding a userId wins; key = `discord:user:${userId}`
if (currentState.participantKey === nextState.participantKey &&
    currentState.participantLabel === nextState.participantLabel &&
    currentState.sessionId === nextState.sessionId) {
    return participant;                      // unchanged ⇒ skip the disk write
}
await persistMergedThreadState(input.thread, input.bindingsPath, nextState, input.errorLabel);
```

**Flow:** try the adapter-normalized author first (raw.author must NOT win — bot-authored raw payloads carry misleading authors) → walk the eight raw slots, which cover gateway messages AND interaction command payloads (user hidden at `data.member.user`) → build `discord:user:{id}` with a label from fullName/global_name/displayName/username/id → load current thread state, merge participant fields, skip the write when key+label+sessionId are all unchanged → persist merged state otherwise.
**Invariant:** (1) A participant CHANGE never changes sessionId — the thread keeps its bound RPC session across speakers (test-pinned: bob's message on alice's session leaves `session-alice` in both the root and state slots). (2) No userId ⇒ no participant and no write. (3) Unchanged context performs zero disk I/O.
**Probe:** `apps/cli/src/connectors/adapters/discord.test.ts` — "resolves Discord participants from normalized gateway message authors" (raw bot author does not win), "resolves Discord interaction users even when raw.data is command data" (`data.member.user` found), "updates Discord participant metadata without changing the thread session" (participant updated, sessionId untouched).

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", file: "apps/cli/src/connectors/adapters/discord.ts", symbol: "persistDiscordThreadContext" });
```

## Verdict
Adopt the separation: participant identity is mutable per-turn metadata; session identity is stable binding state — persist the former without touching the latter, and skip writes when nothing changed. Adapt the raw-payload slot list to the platform's event shapes. Omit nothing — the session-stability invariant is the point. Coverage caveat: fully test-pinned including the interaction-payload slot.
