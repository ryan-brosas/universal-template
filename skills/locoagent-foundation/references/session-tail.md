<!-- capsule-v2 -->
# Session JSONL tailing with offset+uuid dedup — how do you live-monitor an agent's trajectory file without re-printing or losing entries?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the correct read loop for following a JSONL session log that grows while you watch it, and which entry types matter to a human operator?

## Offset-tracked byte reader + uuid-seen filter
**Path/Symbol:** `scripts/tail-agent.ts`:`watchFile` (`:161-208`), `getLatestSession` (`:130-142`), `printEntry` (`:41-128`), `watchLatest` (`:210-227`).
**Signature:** `watchFile(filePath: string, fromStart = false): Promise<void>`; `getLatestSession(): Promise<string | null>` (max-mtime `.jsonl` scan).
**Data Shape:** Claude-Code-style session JSONL: `entry { type, timestamp, uuid?, message?, isMeta? }`; `type` ∈ assistant (content blocks text/tool_use/thinking) | user (tool_result) | queue-operation (enqueue). State: integer byte `offset`, string carry `buffer`, `Set<string> seenUuids`.

### Decisive source
```ts
const seenUuids = new Set<string>()
while (true) {
  const fh = await open(filePath, 'r')
  const s = await fh.stat()
  if (s.size > offset) {
    const newBytes = s.size - offset
    const buf = Buffer.alloc(newBytes)
    await fh.read(buf, 0, newBytes, offset)
    offset = s.size                    // advance BEFORE parse; failures skip forward anyway
    buffer += buf.toString('utf8')
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''         // last chunk may be partial — carry it over
    for (const line of lines) {
      try {
        const entry = JSON.parse(line.trim())
        const uuid = entry.uuid as string | undefined
        if (uuid && seenUuids.has(uuid)) continue   // rewrite/retry double-emission guard
        if (uuid) seenUuids.add(uuid)
        printEntry(entry)
      } catch { /* skip malformed lines */ }
    }
  }
  await fh.close()
  await Bun.sleep(POLL_INTERVAL_MS)    // 200 ms poll; no fs.watch dependency
}
```

**Flow:** default mode stats the latest `*.jsonl` by mtime and starts at END-of-file (`offset = size`) so the operator sees only new activity; `--from-start` replays history → each 200 ms tick reads only `[offset, size)`, advances the offset, splits on `\n`, carries the trailing partial line in `buffer` until its newline arrives, dedups by `uuid`, then prints per type: assistant `text` blocks verbatim, `tool_use` condensed (Bash command ≤120 chars, TodoWrite active item only, other tools ≤100 chars of JSON), thinking ≤150 chars, user `tool_result` ≤200 chars or a `(N chars)` placeholder, `isMeta` skill-injection rows skipped entirely, `queue-operation enqueue` printed as a task banner. `watchLatest` polls every 1 s and switches files when a newer session appears.
**Invariant:** Never parse a partial line — only complete `\n`-terminated chunks leave `buffer`. Never re-emit — uuid set guards duplicate delivery. Offset math is in BYTES on the raw file, not characters. Rendering is a one-way projection: truncation limits exist so a monitor can never flood the terminal that the agent session itself is writing to.
**Probe:** No upstream test file for tail-agent.ts (interactive monitor). Deterministic source-grounded probes: offset advance at `tail-agent.ts:180-184`, partial-line carry at `:187-188`, uuid guard at `:195-197`, isMeta skip at `:102`. Coverage caveat recorded; port with your own fixture test appending lines to a temp JSONL.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "tail-agent session jsonl watch", limit: 10 });
```
Graph resolves `watchFile` :161, `getLatestSession` :130, `printEntry` :41 line-exact.

## Verdict
Adopt the offset+partial-carry+uuid-dedup reader loop (it is host-agnostic beyond Node fs), start-at-end semantics with explicit --from-start opt-in, and type-condensed rendering with hard length caps. Adapt the entry schema to your agent's transcript format and the ANSI palette to your terminal. Omit the hardcoded project-dir path — derive it from your harness's session storage convention.
