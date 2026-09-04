<!-- capsule-v2 -->
# Database-queues infinite-query plane — how does an infiniteQuery page through a UNION ALL of two physical tables without dropping rows that share a timestamp?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What guard ladder, status-to-SQL composition, and cursor machinery does a message-list infinite query need when its rows live in two tables (live queue + archive) and the natural sort column is not unique?

## Guard ladder + status tri-state composition (`data/database-queues/database-queue-messages-infinite-query.ts`)
**Path/Symbol:** `apps/studio/data/database-queues/database-queue-messages-infinite-query.ts` : `getDatabaseQueue` (:37-106), `QUEUE_MESSAGES_PAGE_SIZE` (:33).
**Signature:** `getDatabaseQueue({ projectRef, connectionString, queueName, after, status }): Promise<DatabaseQueueData>` where `after: { enqueuedAt: string; msgId: number } | undefined`.
**Data Shape:** guard order — projectRef required → `isQueueNameValid` (alphanumeric/underscore/hyphen only; the name is interpolated into table names via `ident`) → `status.length === 0` returns `[]` WITHOUT a SQL hop. Status tri-state for the queue-table arm: available+scheduled ⇒ no `vt` filter; available-only ⇒ `WHERE vt < now`; scheduled-only ⇒ `WHERE vt > now`, with `now = literal(dayjs(new Date()).format(DATE_FORMAT))`. The archived arm is independent and selected by `status.includes('archived')`; the two arms differ in one column — the queue arm projects `NULL as archived_at` so the UNION ALL shapes line up. Non-null arms are joined with a reduce into `UNION ALL`.

### Decisive source
```ts
if (status.length === 0) {
  return []
}

// handles when scheduled and available are deselected
const queueTable = safeSql`${ident('pgmq')}.${ident(pgmqQueueTable(queueName))}`
const archivedTable = safeSql`${ident('pgmq')}.${ident(pgmqArchiveTable(queueName))}`
const nowLiteral = literal(dayjs(new Date()).format(DATE_FORMAT))

let queueQuery: SafeSqlFragment | null = null
if (status.includes('available') && status.includes('scheduled')) {
  queueQuery = safeSql`SELECT msg_id, enqueued_at, read_ct, vt, message, NULL as archived_at FROM ${queueTable}`
} else if (status.includes('available') && !status.includes('scheduled')) {
  queueQuery = safeSql`... FROM ${queueTable} WHERE vt < ${nowLiteral}`
} else if (!status.includes('available') && status.includes('scheduled')) {
  queueQuery = safeSql`... FROM ${queueTable} WHERE vt > ${nowLiteral}`
}
```

**Flow:** compose at most two SELECT fragments (queue arm, archive arm), UNION ALL them, wrap in a derived table `combined`, apply the cursor predicate + `order by enqueued_at, msg_id LIMIT 30`, execute through pass-1's `executeSql` guard ladder.
**Invariant:** every arm of a UNION ALL must project the same column list — the `NULL as archived_at` placeholder on the queue arm is what makes that legal; drop it and the union fails or silently misaligns columns. An empty filter set short-circuits before any SQL is composed: a no-op fetch must not cost a database round trip.
**Probe:** direct read at the pin; the module test does not cover the tri-state (it pins only the cursor — see below).

## Composite keyset cursor over a non-unique sort column
**Path/Symbol:** same file : cursor comment + `whereClause` (:80-90), final SQL (:90-95).
**Signature:** `QueueMessagesPageParam = { enqueuedAt: string; msgId: number }`.
**Data Shape:** the in-source rationale: `enqueued_at` is NOT unique — pgmq defaults it to `now()`, so every message from one `send_batch` shares a timestamp. A plain `enqueued_at > last` cursor skips the rows that share the last page's timestamp, dropping them from the list. `msg_id` is unique within each table and breaks the tie.

### Decisive source
```ts
// Keyset pagination on a composite (enqueued_at, msg_id) cursor. enqueued_at is
// not unique: pgmq defaults it to now(), so every message from one send_batch
// shares a timestamp. A plain `enqueued_at > last` cursor skips the rows that
// share the last page's timestamp, dropping them from the list. msg_id is unique
// within each queue/archive table and breaks the tie.
const whereClause = after
  ? safeSql` WHERE (enqueued_at, msg_id) > (${literal(after.enqueuedAt)}, ${literal(after.msgId)})`
  : safeSql``

const sql = safeSql`SELECT * FROM (${unionFragment}) AS combined${whereClause} order by enqueued_at, msg_id LIMIT ${literal(QUEUE_MESSAGES_PAGE_SIZE)}`
```

**Flow:** page N+1's predicate is a row-value comparison against the LAST row of page N; the ORDER BY must match the cursor tuple exactly or pages can overlap/gap under concurrent inserts.
**Invariant:** a keyset cursor is only as strong as its uniqueness guarantee — if the leading sort column can repeat, the cursor tuple MUST include a per-row-unique tie-breaker, and the ORDER BY must carry the same tuple in the same order. This generalizes pass-3's table-rows capsule (which used a unique keyset directly); here the "natural" time column is non-unique, so the composite is mandatory, not optional.
**Probe:** `apps/studio/data/database-queues/database-queue-messages-infinite-query.test.ts` (pure vitest, read whole; unexecutable in-lane — standing block) pins both halves: later pages contain `(enqueued_at, msg_id) > (` AND do NOT match `/WHERE enqueued_at >\s/` (the old single-column form that dropped batch-mates); the first page omits the predicate but still orders by the unique key.

## InfiniteQuery wiring + keys deviation
**Path/Symbol:** same file : `useQueueMessagesInfiniteQuery` (:108-143); `keys.ts` : `databaseQueuesKeys.getMessagesInfinite` (:5-6).
**Signature:** `useQueueMessagesInfiniteQuery<TData>({ projectRef, connectionString, queueName, status }, options?)`.
**Data Shape:** `staleTime: 0`; `initialPageParam: undefined`; `getNextPageParam(lastPage)` = full-page heuristic — `lastPage.length >= QUEUE_MESSAGES_PAGE_SIZE` then `last(lastPage)` → `{ enqueuedAt: lastRow.enqueued_at, msgId: lastRow.msg_id }`. enabled gate: `enabled && typeof projectRef !== 'undefined'`.

### Decisive source
```ts
getNextPageParam(lastPage) {
  const hasNextPage = lastPage.length >= QUEUE_MESSAGES_PAGE_SIZE
  if (!hasNextPage) return undefined
  const lastRow = last(lastPage)
  if (!lastRow) return undefined
  return { enqueuedAt: lastRow.enqueued_at, msgId: lastRow.msg_id }
}
// keys.ts:
getMessagesInfinite: (projectRef: string | undefined, queueName: string, options?: object) =>
  ['projects', projectRef, 'queue-messages', queueName, options].filter(Boolean),
```

**Flow:** the hook threads `pageParam` into `getDatabaseQueue({..., after: pageParam})`; react-query accumulates pages as `InfiniteData`. The cache key embeds the `options` object (the status array) so different status selections are distinct cache entries.
**Invariant:** the full-page heuristic (`length >= PAGE_SIZE`) is correct ONLY because the server-side LIMIT is exactly PAGE_SIZE — a short page is the end-of-data signal; if the backend ever filters rows client-side after the limit, the loop stops early. Note the DEVIATION from pass-1's data-module recipe: `.filter(Boolean)` drops an undefined projectRef from the key instead of gating on it — the enabled gate still prevents the fetch, but the key shape for an undefined ref is NOT rooted at `['projects', ...]`, so broad prefix invalidation (pass-1's contextual sweep) will not match it. Porters choosing this pattern must keep the enabled gate as the real protection.
**Probe:** no upstream test for the hook itself (the module test covers `getDatabaseQueue`'s SQL only); confirmed by direct read at the pin.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct whole-file reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "getDatabaseQueue useQueueMessagesInfiniteQuery getNextPageParam QueueMessagesPageParam", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the composite-cursor rule (non-unique sort column ⇒ append a per-row-unique tie-breaker to BOTH the row-value predicate and the ORDER BY), the empty-filter short-circuit before SQL composition, the placeholder-column trick for UNION ALL shape alignment, and the full-page hasNextPage heuristic. Adapt the status tri-state to your own visibility semantics and the pgmq table-name helpers to your extension layout. Omit the `.filter(Boolean)` key deviation unless you have a reason to unroot the key — prefer pass-1's rooted-keys + enabled-gate recipe. Caveat: the cursor tuple assumes `msg_id` uniqueness WITHIN each arm; if you merge arms whose id spaces collide, add the arm identity to the tuple.
