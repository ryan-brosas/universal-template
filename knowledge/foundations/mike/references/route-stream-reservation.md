<!-- capsule-v2 -->
# Route stream reservation — how does SSE persistence survive crashes and concurrent streams?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** How do you persist a streamed assistant turn so a mid-stream crash or a second concurrent POST can't corrupt or duplicate history?

## Pre-insert null reservation row + id-scoped 3-attempt updater
**Path/Symbol:** `backend/src/lib/chat/routeStreaming.ts:7` (`reserveAssistantMessage`), `:23` (`createReservedAssistantMessageUpdater`), `:46` (`withoutEmptyAssistantReservations`), `:54` (`openAssistantSse`). Consumers: `enrichWithPriorEvents` + `appendAssistantEventsToLastAssistantMessage` both `.not("content","is",null)`.
**Signature:** `reserveAssistantMessage({db, table, id, chatId}) -> error|null`; updater factory returns `(content, citations) => Promise<error|null>`.
**Data Shape:** assistant rows pre-insert with `content:null, citations:null` and a CLIENT/route-chosen uuid `id`; two legal tables ("chat_messages" | "word_chat_messages").

### Decisive source
```ts
return async (content, citations) => {
    if (args.enabled === false) return null;          // disabled = no-op, still resolves
    for (let attempt = 0; attempt < 3; attempt += 1) {
        const result = await args.db.from(args.table)
            .update({ content, citations })
            .eq("id", args.id).eq("chat_id", args.chatId);   // scoped BOTH ways
        lastError = result.error;
        if (!lastError) return null;
    }
    return lastError;
};
```

**Flow:** reserve (id pre-claimed → duplicate POST hits pk conflict instead of double-insert) → stream with periodic/retryable updates via the bound updater → readers of "last assistant message" filter out null-content reservations so crashed streams leave no phantom turns.
**Invariant:** The reservation row is the crash record: content=null means "never completed" everywhere downstream. Updates are keyed by (id, chat_id), never by recency ordering — no race can retarget the update at a different row. SSE headers include `X-Accel-Buffering: no`, and `res.on("close")` abort signals the generator when the client disconnects before finish.
**Probe:** `grep -c 'reserveAssistantMessage\|withoutEmptyAssistantReservations' src/routes/chat.ts src/routes/projectChat.ts src/routes/wordChat.ts 2>/dev/null | grep -v ':0'` lists chat.ts + wordChat.ts; integration suites under `src/__tests__/integration/*.routes.test.ts` mock the streaming path (green at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "reserveAssistantMessage createReservedAssistantMessageUpdater withoutEmptyAssistantReservations openAssistantSse", limit: 10 });
```

## Verdict
Adopt reserved-row persistence + null-means-crashed reader contract + bounded retry updater as portable contracts; adapt to your DB/upsert semantics; omit Express header specifics.
