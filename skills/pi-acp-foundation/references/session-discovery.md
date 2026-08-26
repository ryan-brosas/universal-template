<!-- capsule-v2 -->
# Session discovery — read pi's own JSONL session files for list/load

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter list and find pi sessions by reading pi's own JSONL session files (title/updatedAt ladders, bounded tail scanning)?

## Session discovery
**Path/Symbol:** `src/acp/pi-sessions.ts` (whole, 333L).
**Signature:** `getPiSessionsDir(): string`; `listPiSessions(): PiSessionListItem[]`; `findPiSession(sessionId): PiSessionListItem | null`; `findPiSessionFile(sessionId): string | null`.
**Data Shape:** `PiSessionListItem = { sessionId, cwd, title, updatedAt, sessionFile }`. Sessions dir = `PI_CODING_AGENT_DIR` override or `~/.pi/agent`, honoring `settings.json` `sessionDir` (resolved relative to agentDir). Files are `.jsonl` under that dir (recursive walk).

### Decisive source
```ts
export function listPiSessions(): PiSessionListItem[] {
  const files: string[] = []
  walkJsonlFiles(getPiSessionsDir(), files)   // recursive .jsonl walk
  for (const file of files) {
    const header = parseSessionHeader(readFirstLine(file))   // {type:'session', id, cwd}
    if (!header) continue
    let title = pickTitleFromTail(tail)        // last session_info.name in tail window
    let updatedAt = pickUpdatedAtFromTail(tail) // last message timestamp, else any timestamp
    if (!title) title = scanSessionInfoNameFromFile(file)  // full-file scan if name fell out of tail window
    if (!updatedAt) updatedAt = statSync(file).mtime.toISOString()
    if (!title) title = pickFallbackTitleFromHead(file)     // first user message, 80 chars
    items.push({ sessionId: header.sessionId, cwd: header.cwd, title, updatedAt, sessionFile: file })
  }
  items.sort((a,b) => (b.updatedAt ?? '').localeCompare(a.updatedAt ?? ''))   // most recent first
  return items
}
```
```ts
// bounded reads: head 64KB for the first line, tail 256KB for title/updatedAt
const DEFAULT_TAIL_BYTES = 256 * 1024
const DEFAULT_HEAD_BYTES = 64 * 1024
```

**Flow:** Recursively walk the sessions dir for `.jsonl` files; read the first line (bounded head) to parse the `session` header (`id`/`cwd`); read the tail (bounded 256KB) to find the last `session_info.name` (title) and last `message` timestamp (updatedAt); fall back to a full-file scan for an old name, `mtime` for updatedAt, and the first user message for the title; sort most-recent-first.

**Invariant:** Reads are bounded (head 64KB, tail 256KB) so listing many large session files stays fast; updatedAt prefers the last `message` timestamp (matching pi's `/resume` ordering) over `mtime`; a session with no messages still gets a valid timestamp.

**Probe:** `test/component/session-list-and-load.test.ts`, `test/component/session-list-scoped.test.ts`, `test/component/session-title-long-session.test.ts` ("session title from tail"), and `test/component/session-updatedAt-message-only.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "listPiSessions pickTitleFromTail pickUpdatedAtFromTail", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bounded JSONL session-file reading, the title/updatedAt fallback ladders, and the most-recent-first sort. Adapt the session-file format (header/title/timestamp keys) and the sessions-dir resolution to the target agent. Omit the `scanSessionInfoNameFromFile`/`pickFallbackTitleFromHead` full-file fallbacks unless the target's session files grow large.
