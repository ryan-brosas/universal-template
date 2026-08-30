<!-- capsule-v2 -->
# Scratchpad — line-preserving checklist mutations that never delete hand-written notes

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent maintain a Markdown checklist (`- [ ] text`) with invisible timestamp meta while preserving every non-checklist line a user may have hand-written?

## Scratchpad
**Path/Symbol:** `index.ts:parseScratchpad` (563–582), `serializeScratchpad` (584–594), `scratchpadAdd` (619–625), `scratchpadToggle` (627–643), `scratchpadClearDone` (645–662).
**Signature:** `parseScratchpad(content): ScratchpadItem[]`; `serializeScratchpad(items): string`; `scratchpadAdd(content, text, meta): string`; `scratchpadToggle(content, needle, done): {content, matched}`; `scratchpadClearDone(content): {content, removed}`.
**Data Shape:** `ScratchpadItem = { done: boolean; text: string; meta: string }`. Item regex `^- \[([ xX])\] (.+)$`; meta is the `<!-- ts [sid] -->` comment on the line directly above an item. `SCRATCHPAD_ITEM_REGEX` and `SCRATCHPAD_META_COMMENT_REGEX` gate the line-preserving ops.

### Decisive source
```ts
// scratchpadToggle (627-643): operate on raw lines; only rewrite the matched item
for (let i = 0; i < lines.length; i++) {
  const m = lines[i].match(SCRATCHPAD_ITEM_REGEX);
  if (!m) continue;
  if ((m[1].toLowerCase() === "x") === done) continue;   // already in target state
  if (!m[2].toLowerCase().includes(lower)) continue;      // substring match
  lines[i] = `- [${done ? "x" : " "}] ${m[2]}`;
  return { content: lines.join("\n"), matched: true };
}
return { content, matched: false };

// scratchpadClearDone (645-662): drop done items AND their timestamp comment above
if (m && m[1].toLowerCase() === "x") {
  removed++;
  if (out.length > 0 && SCRATCHPAD_META_COMMENT_REGEX.test(out[out.length - 1])) out.pop();
  continue;
}
out.push(line);
```

**Flow:** (1) `parseScratchpad` walks lines, matching checklist items and capturing the meta comment on the preceding line. (2) `serializeScratchpad` rebuilds a `# Scratchpad` skeleton from items. (3) `scratchpadAdd` appends `meta\n- [ ] text` to the raw content (or builds the skeleton for empty). (4) `scratchpadToggle` rewrites only the matched line, preserving every other line. (5) `scratchpadClearDone` removes done items and their immediately-above timestamp comment, keeping everything else.

**Invariant:** the old parse→mutate→serialize round-trip silently deleted non-checklist content (hand-written notes, headers, sub-bullets) on first write; these line-preserving ops guarantee unknown content survives every mutation.

**Probe:** `test/unit.test.ts` — `line-preserving scratchpad mutations` describe (:2083): `scratchpadAdd appends and preserves all existing content` (:2098), `scratchpadToggle flips only the matched item` (:2112), `scratchpadToggle can uncheck a done item` (:2120), `scratchpadToggle reports no match honestly` (:2126), `scratchpadClearDone removes done items and their meta, keeps the rest` (:2130), `scratchpadClearDone preserves hand-written HTML comments` (:2140). Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "scratchpadAdd scratchpadToggle scratchpadClearDone parseScratchpad serializeScratchpad", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the line-preserving scratchpad mutations, the `- [ ]` item format with timestamp meta, the substring toggle, and the meta-comment removal on clear-done. Adapt the item/meta regexes and the file name to the host. Omit nothing here — this is the portable scratchpad core.
