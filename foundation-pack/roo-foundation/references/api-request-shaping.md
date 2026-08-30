<!-- capsule-v2 -->
# API-request shaping — which repairs make a stored history legal to SEND without mutating what is stored?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Storage keeps interleaved/duplicate/summary-tagged messages for faithful rewind — where does send-time legality get enforced?

## mergeConsecutiveApiMessages + validateAndFixToolResultIds: shaping-only pipeline
**Path/Symbol:** `src/core/task/mergeConsecutiveApiMessages.ts:23-59`; `src/core/task/validateToolResultIds.ts:49-199` (`validateAndFixToolResultIds`); wired at `src/core/task/Task.ts:4083-4089` (send path) and :981-1082 (history-add path).
**Signature:** `mergeConsecutiveApiMessages(messages, { roles?: Role[] })` default roles `["user"]`; `validateAndFixToolResultIds(userMessage, apiConversationHistory): MessageParam`.
**Data Shape:** Merge guard flags: `!msg.isSummary && !prev.isTruncationMarker && !msg.isTruncationMarker`; merged ts = `Math.max(prev.ts ?? 0, msg.ts ?? 0) || prev.ts || msg.ts`.

### Decisive source
```ts
// merge: regular messages may fold INTO a summary (API-only), never the reverse
const canMerge = prev && prev.role === msg.role && mergeRoles.has(msg.role) &&
                 !msg.isSummary && !prev.isTruncationMarker && !msg.isTruncationMarker
// validate: dedupe tool_results FIRST (defensive net for approval-race dupes #10465),
// then position-match remaining blocks by OBJECT IDENTITY (indexOf), not id equality
const toolResultIndex = toolResults.indexOf(block as Anthropic.ToolResultBlockParam)
if (toolResultIndex !== -1 && toolResultIndex < toolUseBlocks.length) {
  const correctId = toolUseBlocks[toolResultIndex].id
  if (!usedToolUseIds.has(correctId)) return { ...block, tool_use_id: correctId }
}
return null // unmatchable duplicate/orphan ⇒ dropped
// finally: synthetic results "Tool execution was interrupted before completion."
// are PREPENDED so they precede any summarizing text blocks
```

**Flow:** effective history → since-last-summary slice → consecutive-user merge → image-strip → send. On history ADD, the incoming user message is validated against the previous assistant turn (dedupe → fix-by-position → drop orphans → synthesize missing results). Docstring contract: merging is for *API request shaping only* — never persist merged output, or rewind loses individual message boundaries.
**Invariant:** Summary/truncation-marker messages are merge boundaries; identity-based position matching handles duplicate ids correctly where naive id-matching collapses them; missing tool_results get placeholder content rather than protocol-violating omissions.
**Probe:** `src/core/task/__tests__/mergeConsecutiveApiMessages.spec.ts` ("does not merge a summary into a preceding message" :36); `validateToolResultIds.spec.ts` (position-fix matrix :104-179, duplicate-terminal-fallback :477, orphan filtering :350).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "mergeConsecutiveApiMessages validateAndFixToolResultIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer repair (dedupe→position-fix→synthesize, then role-merge with summary boundaries) as a pure pre-send pass. Adapt the placeholder strings. Omit the Anthropic block-type plumbing specifics if your wire format differs.
