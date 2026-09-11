<!-- capsule-v2 -->
# Memory budget & dual-channel parity — how do you cap what memory costs context without ever losing content, when the same memories can arrive through TWO channels?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does the agent bound oversized memory files and keep "what's actually in my context" accounting correct when memories deliver both as prompt injection AND as attachments?

## Budget gate + channel-parity filter

**Path/Symbol:** `src/utils/agentmd.ts`:`MAX_MEMORY_CHARACTER_COUNT`, `getLargeMemoryFiles`, `filterInjectedMemoryFiles` (`:92`, `:1132-1152`).
**Signature:** `getLargeMemoryFiles(files: MemoryFileInfo[]): MemoryFileInfo[]`; `filterInjectedMemoryFiles(files: MemoryFileInfo[]): MemoryFileInfo[]`.
**Data Shape:** Threshold constant `MAX_MEMORY_CHARACTER_COUNT = 40000` (chars of `file.content`). `AutoMem`/`TeamMem` file types are the attachment-delivered classes; all other types ride the system prompt.

### Decisive source
```ts
export function getLargeMemoryFiles(files: MemoryFileInfo[]): MemoryFileInfo[] {
  return files.filter(f => f.content.length > MAX_MEMORY_CHARACTER_COUNT)
}

// When tengu_moth_copse is on, the findRelevantMemories prefetch surfaces
// memory files via attachments, so the MEMORY.md index is no longer injected
// into the system prompt. Callsites that care about "what's actually in
// context" should filter through this.
export function filterInjectedMemoryFiles(files: MemoryFileInfo[]): MemoryFileInfo[] {
  const skipMemoryIndex = getFeatureValue_CACHED_MAY_BE_STALE('tengu_moth_copse', false)
  if (!skipMemoryIndex) return files
  return files.filter(f => f.type !== 'AutoMem' && f.type !== 'TeamMem')
}
```

**Flow:** Producers always load EVERYTHING (`getMemoryFiles` never truncates). Consumers split by need: the status line (`src/utils/status.tsx:118`) and `/doctor` context warnings (`src/utils/doctorContextWarnings.ts:44`) run `getLargeMemoryFiles` to WARN ("this memory exceeds 40k chars") and show a status notice (`src/utils/statusNoticeDefinitions.tsx:34-36`) instead of dropping anything; the context builder (`src/context.ts:172`) and `/context` analyzer (`src/utils/analyzeContext.ts:329`) run `filterInjectedMemoryFiles` so their accounting counts only what the current feature-flag channel actually injects.
**Invariant:** The budget is ADVISORY — over-limit files are surfaced and warned about, never truncated or dropped (content loss is worse than bloat). Channel PARITY is the real invariant: when the prefetch flag flips memory delivery to attachments, any consumer reasoning about live context MUST pass files through the identical filter, or it counts ghost injections that are not in the prompt. Flag reads go through the CACHED_MAY_BE_STALE getter so call sites stay synchronous.
**Probe:** No direct test file covers these exports (coverage caveat — claims source-grounded via caller reads). Deterministic probe: grep pins `MAX_MEMORY_CHARACTER_COUNT = 40000` at `src/utils/agentmd.ts:92`; `search_graph --name-pattern "^(getLargeMemoryFiles|filterInjectedMemoryFiles)$"` resolves `locoagent.src.utils.agentmd.*`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "memory budget large files injected filter attachments", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the warn-don't-truncate budget posture and the shared consumer-side filter that keeps dual delivery channels consistent for context accounting. Adapt the threshold value and the feature-flag name to your host. Omit nothing from the parity rule — filtering in one consumer and not another is exactly the drift this seam exists to prevent.
