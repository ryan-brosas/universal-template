<!-- capsule-v2 -->
# Normalize + filter-noise front stage — which messages become blocks, and what never reaches the section builders?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What is the exact block grammar every downstream extractor relies on, and which noise classes are dropped before any extraction?

## normalize → filterNoise (`src/compaction/normalize.ts`, `src/compaction/filter-noise.ts`)
**Path/Symbol:** `src/compaction/normalize.ts:normalize/normalizeOne` (:6-73); `src/compaction/filter-noise.ts:filterNoise` (:31-47), `NOISE_TOOLS` (:3-11), `XML_WRAPPER_RE` (:19-20).
**Signature:** `normalize(messages: Message[]): NormalizedBlock[]`; `filterNoise(blocks): NormalizedBlock[]`.
**Data Shape:** Six block kinds: `user{text}`, `assistant{text}`, `tool_call{name,args}`, `tool_result{name,text,isError}`, `bash{command,output,exitCode}`, `thinking{text,redacted}` — all carry optional `sourceIndex` (original message index, later rendered as `(#N)` refs).

### Decisive source
```ts
if (msg.role === 'user') {
  const text = sanitize(textOf(msg.content));
  if (text) blocks.push({kind:'user', text, sourceIndex});
  // image parts become `[image: <mime>]` user blocks
  return blocks.length > 0 ? blocks : [{kind:'user', text:'', sourceIndex}];  // NEVER empty
}
// bashExecution is a pi-specific role with command/output/exitCode fields
```
Filter drops: ALL thinking; tool_call/tool_result whose name ∈ {TodoWrite,TodoRead,ToolSearch,WebSearch,AskUser,ExitSpecMode,GenerateDroid}; user blocks containing noise strings ("Continue from where you left off.", "No response requested.", "IMPORTANT: TodoWrite was not called yet.") or EMPTY after XML-wrapper strip (`<system-reminder|ide_opened_file|command-message|context-window-usage>…</\1>`); surviving user text gets the same wrapper-strip.

**Flow:** sanitize (CRLF→LF, ANSI CSI strip, control-char strip) runs INSIDE normalize per block; filter is a pure second pass. Order normalize→filter is contractual: mid-run signals AND compaction both call `filterNoise(normalize(...))`.
**Invariant:** (1) User normalization NEVER returns an empty array (placeholder empty-text block preserves turn structure). (2) Thinking blocks exist in the grammar but are ALWAYS dropped at filter — extractors may assume none. (3) Noise-tool results are dropped WITH their calls, so call/result pairing logic must run AFTER filtering. (4) XML wrappers are stripped from kept user text, not just used for drop-detection.
**Probe:** `tests/full-fidelity-snapshot.test.ts` — `normalizes user messages` (:9), `normalizes bashExecution messages` (:70), `strips thinking blocks from assistant content` (:88), `removes noise tool calls (TodoWrite, etc.)` (:117), `removes XML wrapper noise from user messages` (:129).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "normalize filterNoise NOISE_TOOLS XML_WRAPPER_RE", limit: 8 });
```

## Verdict
Adopt the six-kind block grammar + the three noise classes. Adapt role names and the noise-tool set to your host's vocabulary. Omit bashExecution handling if your host has no dedicated shell-message role.
