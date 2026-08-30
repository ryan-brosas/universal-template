<!-- capsule-v2 -->
# Dropped-work summaries — what the model learns about its own deleted actions

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** When compaction deletes tool traffic, how is that work re-surfaced so the model doesn't repeat or contradict it?

## Structured activity extraction with diff-derived edit ranges, attached to surviving prompts
**Path/Symbol:** `sdk/packages/core/src/extensions/context/compaction-shared.ts:549-623` (`summarizeToolActivity`, `extractDiffLineRange`) + `basic-compaction.ts:81-114` (`buildDroppedWorkSummaryBlock`, `userContentBlocks`).
**Signature:** `summarizeToolActivity(messages) → {readFiles[], editedFiles[], commands[]}`; block text: `<SYSTEM_NOTICE>\nEarlier context was compacted. Summary of your actions after the request above:\nFiles read:\n…\n\nFiles edited:\n…\n\nCommands ran:\n…\n\nYour recent responses:\n…</SYSTEM_NOTICE>`.
**Data Shape:** Reads render as `path:start-end` when read_files inputs carry line ranges; edits get ranges by scanning the matching editor tool RESULT for a numbered diff (`(?:^|\n|\\n)[-+](\d+): `, min/max line seen) after one JSON unwrap (`{result:"..."}`); commands truncate at 100 chars. Editor paths are keyed by tool_use id in a Map and consumed on result arrival.

### Decisive source
```ts
// Editor calls whose results fell outside the span still count as edits.
for (const path of editorPathsByToolUseId.values()) {
    pushUniqueEntry(editedFiles, path);
}
```
```ts
// Attached files and images are stale context bloat once the turn is
// old enough to compact; ... Only the latest typed prompt keeps its attachments.
return message.content.filter(
    (block) => block.type !== "file" && block.type !== "image",
);
```

**Flow:** for each gap of removed messages between surviving typed prompts → summarizeToolActivity over exactly the removed slice (resolved via original-index-by-id map) → prepend the SYSTEM_NOTICE block BEFORE the later prompt's content; gaps after a turn's last surviving message append the summary TO that message; up to 3 most-recent assistant text contents (PRESERVED_ASSISTANT_TEXT_COUNT) ride verbatim inside the covering notice ("Your recent responses"). Empty slices produce no notice.
**Invariant:** Unmatched editors still count as edits (result outside the dropped span must not erase the edit from history); every list is unique+order-preserving (`pushUniqueEntry`), unlike the sorted merge used for compaction-summary metadata folding. Attachments are dropped from all but the LATEST typed prompt — load-bearing attachments may only live on the active request.
**Probe:** `grep -cF '(?:^|\n|\\n)[-+](\d+): ' …/compaction-shared.ts` → 1; `grep -cF 'COMMAND_SUMMARY_CHAR_LIMIT = 100' …/compaction-shared.ts` → 1; upstream test "bridges merged user turns with dropped-work summaries and drops stale metrics".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "summarizeToolActivity extractDiffLineRange", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tool_use-id-keyed edit-range extraction and unmatched-editor fallback; adapt tool names (`read_files`/`editor`/`apply_patch`/`run_commands`) to host tool registry; omit the JSON-unwrap heuristic if host results are never double-encoded. Runner blocked honestly; battery greps green.
