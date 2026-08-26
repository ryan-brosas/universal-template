<!-- capsule-v2 -->
# Unified channel JSONL store — how do multiple agents share one append-only feed without a daemon or a database?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How is one channel's state stored so concurrent processes can append and read it with zero locking infrastructure?

## Unified JSONL: header line + append-only event lines
**Path/Symbol:** `channel.ts:appendChannelEventLine` (:182-211), `channel.ts:readChannelEventLines` (:164-176), `channel.ts:pruneChannelEvents` (:217-234).
**Signature:** `appendChannelEventLine(dirs: Dirs, channelId: string, eventLine: string, meta?: Partial<ChannelRecord>): void`.
**Data Shape:** File = `<base>/channels/<normalized-id>.jsonl`. Line 1 = `ChannelMetaHeader` (`_meta:true`, `v`, `id`, `type:'session'|'named'`, ISO timestamps). Lines 2+ = raw JSON event strings (`FeedEvent`). All writes are plain `fs.writeFileSync`/`appendFileSync` — no lock files anywhere.

### Decisive source
```ts
if (!fs.existsSync(filePath)) {
  // Create new file with minimal metadata header
  const header: ChannelMetaHeader = { _meta: true, v: CHANNEL_META_VERSION, ... };
  fs.writeFileSync(filePath, JSON.stringify(header) + '\n' + eventLine + '\n');
} else {
  fs.appendFileSync(filePath, eventLine + '\n');
}
```

**Flow:** normalize id → path → if missing, write header+first-event atomically in ONE write call; else append single line → every reader splits on `\n`, drops line 0 via `slice(1)`, filters blanks, tolerates unparsable lines by skipping.
**Invariant:** The metadata header is ALWAYS exactly line 1; readers skip it positionally (`lines.slice(1)`) not by parsing every line — reordering or blank first line silently breaks every consumer. Append-only means "tail reads are recent reads"; pruning rewrites header+tail-N through a tmp-file+rename in `writeChannel` (:266-284) but plain append never rewrites.
**Probe:** `grep -c "JSON.stringify(header)" channel.ts` (=1, only the create-new branch); `grep -n "lines.slice(1)" channel.ts feed/index.ts swarm/task-store/events.ts` (each reader skips line 0); direct test `tests/channel.test.ts::channel-aware registration > tolerates malformed legacy channel files without ids`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "appendChannelEventLine readChannelEventLines pruneChannelEvents", limit: 5 });
```

## Verdict
Adopt the header-line-1 + append-only-lines format and the atomic create-with-first-event write for ANY multi-process agent coordination log; adapt the directory layout (`<project>/.pi/messenger/channels/`) to your host layout; omit the session/named channel-type taxonomy if you have no phrase-named session channels. Caveat: no cross-process file locking — correctness rests on single-line appends being atomic-enough at OS level plus best-effort catch-all error swallowing.
