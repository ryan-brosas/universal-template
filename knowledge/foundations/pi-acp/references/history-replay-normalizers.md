<!-- capsule-v2 -->
# History replay normalizers — role-shaped text extraction with per-role block filters

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** When replaying a restored pi conversation to the ACP client, how is each message role's content flattened, and why are user and assistant normalized by DIFFERENT rules?

## Replay normalizers
**Path/Symbol:** `src/acp/translate/pi-messages.ts` whole file (17L): `normalizePiMessageText(content: unknown): string` (:1-8), `normalizePiAssistantText(content: unknown): string` (:10-17). Consumers: `src/acp/agent.ts:1069` (user) / `:1082` (assistant) inside the loadSession history replay.
**Signature:** both take `unknown` (string OR content-block array) and return concatenated text.

### Decisive source
```ts
export function normalizePiMessageText(content: unknown): string {
  if (typeof content === 'string') return content          // USER: legacy/string form passes through verbatim
  if (!Array.isArray(content)) return ''
  return content.map(c => c?.type === 'text' && typeof c.text === 'string' ? c.text : '')
    .filter(Boolean).join('')
}
export function normalizePiAssistantText(content: unknown): string {
  // Assistant content is typically an array of blocks; only replay text blocks for MVP.
  if (!Array.isArray(content)) return ''                   // ASSISTANT: NO string fast path — non-array → ''
  return /* same text-only join */
}
```

**Flow:** during session restore, `getMessages()` output is replayed chunk-by-chunk into `user_message_chunk` / `agent_message_chunk` updates. User content may legitimately be a bare string in pi's persisted format; assistant content is always a BLOCK ARRAY that mixes `text` with non-replayable blocks (`thinking`, tool calls). Both normalizers keep ONLY `{type:'text'}` blocks — thinking and tool payloads must not re-enter the transcript as message text.

**Invariant:** the asymmetry IS the contract: dropping the user-side string fast-path corrupts every legacy session's first message into empty; adding an assistant-side string pass-through would leak non-text roles if pi ever persists a raw string there. Non-text blocks are FILTERED, never stringified — a porter who JSON-stringifies thinking blocks floods the client with internal reasoning. Empty results yield no update at all (callers guard `if (text)`), not an empty-chunk emission.

**Probe:** `test/unit/pi-messages.test.ts` — "supports string" (:5, user path), "joins text blocks" (:9, mixed non-text dropped), "normalizePiAssistantText: joins only text blocks" (:20, pins `thinking` block filtered out of `'hi!'`). Consumer behavior pinned by `test/unit/startup-info-load-session.test.ts`.
**Coverage:** check_index_coverage `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "normalizePiMessageText normalizePiAssistantText getMessages replay", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both functions verbatim as a PAIR — the string-fast-path asymmetry is deliberate. Adapt only if your agent's persistence format differs per role. Omit nothing; 17 lines port whole.
