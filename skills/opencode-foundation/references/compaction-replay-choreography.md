<!-- capsule-v2 -->
# Compaction replay choreography — how does opencode compact mid-conversation and put the user's turn back afterwards?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How is a compaction run executed as a special assistant turn, how are prior summaries hidden from re-summarization, and how does the interrupted user message get replayed?

## Compaction-turn assembly
**Path/Symbol:** `packages/opencode/src/session/compaction.ts` (`processCompaction` :319–557; serialization helpers :51–113).
**Signature:** `process({parentID, messages, sessionID, auto, overflow?}) → "continue" | "stop"`; `create({sessionID, agent, model, auto, overflow?})` writes the marker pair (:559–582).
**Data Shape:** Parent must be a USER message carrying a `compaction` part (thrown otherwise :327-329). Assistant payload message is stamped `mode:"compaction"`, `agent:"compaction"`, `summary:true` (:398-401). Serialized history is a text protocol: `[User]: …`, `[Attached mime: filename]`, `[Assistant]: …`, `[Assistant reasoning]: …`, `[Assistant tool call]: name(input)`, `[Tool result]: …`, `[Tool error]: …`, and `[Old tool result content cleared]` for parts whose `state.time.compacted` is set.

### Decisive source
```ts
// compaction.ts:363-371 — hide EVERY prior completed compaction pair, chain summaries
const history = compactionPart && messages.at(-1)?.info.id === input.parentID ? messages.slice(0, -1) : messages
const prior = completedCompactions(history)          // pairs: assistant has summary+finish+!error AND parent user has compaction part (:97-113)
const hidden = new Set(prior.flatMap((item) => [item.userIndex, item.assistantIndex]))
const previousSummary = prior.at(-1)?.summary        // only the LATEST summary is carried forward
const selected = yield* select({ messages: history.filter((_, index) => !hidden.has(index)), cfg, model })
// compaction.ts:378-391 — serialize + plugin override points
const msgs = structuredClone(selected.head)
yield* plugin.trigger("experimental.chat.messages.transform", {}, { messages: msgs })
const conversation = msgs.map(serialize).filter(Boolean).join("\n\n")
const nextPrompt = compacting.prompt ?? [buildPrompt({ previousSummary, context: [conversation] }), ...compacting.context].filter(Boolean).join("\n\n")
```

**Flow:** The compaction request itself runs through the SAME processor used for normal turns (`processors.create` → `processor.process`) but with `tools:{}`, `system:[]` and a single synthetic user message (:420-448) — so retries/usage/cost plumbing are reused unchanged. Plugin hooks fire twice: `experimental.session.compacting` can replace the prompt or inject context; `experimental.chat.messages.transform` mutates a CLONE of the head before serialization. When the processor itself overflows, the result "compact" maps to a ContextOverflowError on the compaction message with DIFFERENT copy depending on whether replay was attempted (:450-459) and returns "stop".
**Invariant:** Hiding is by INDEX PAIR — both the old compaction user message AND its summary assistant message must vanish together or the next summary double-counts that span. Only the newest prior summary feeds `previousSummary`; older summaries are intentionally dropped (chained summarization, not concatenated). The parent-marker slice (:363) prevents the CURRENT compaction part from being treated as history.
**Probe:** `packages/opencode/test/session/compaction.test.ts` — `describe("session.compaction.process")` at :814 (drives process end-to-end with fake models); `describe("session.compaction.create")` at :566 asserts the created marker pair `{type:"compaction", auto, overflow}` on a single user message (:571-596).

## Overflow replay ladder
**Path/Symbol:** same file :340–356 (replay selection), :461–466 (tail_start_id sync), :468–549 (replay write + auto-continue).

### Decisive source
```ts
// compaction.ts:341-355 — find the last real user turn BEFORE this overflow, drop media
if (input.overflow) {
  const idx = input.messages.findIndex((m) => m.info.id === input.parentID)
  for (let i = idx - 1; i >= 0; i--) {
    const msg = input.messages[i]
    if (msg.info.role === "user" && !msg.parts.some((p) => p.type === "compaction")) {
      replay = { info: msg.info, parts: msg.parts }
      messages = input.messages.slice(0, i)          // summarize ONLY up to the replay point
      break
    }
  }
  const hasContent = replay && messages.some((m) => m.info.role === "user" && !m.parts.some((p) => p.type === "compaction"))
  if (!hasContent) { replay = undefined; messages = input.messages }   // nothing to replay ⇒ full-history mode
}
// compaction.ts:482-494 — replay parts get NEW ids; media becomes a placeholder narrative
for (const part of replay.parts) {
  if (part.type === "compaction") continue
  const replayPart = part.type === "file" && MessageV2.isMedia(part.mime)
    ? { type: "text", text: `[Attached ${part.mime}: ${part.filename ?? "file"}]` }   // never re-attach oversized media
    : part
  yield* session.updatePart({ ...replayPart, id: PartID.ascending(), messageID: replayMsg.id, sessionID })
}
```

**Flow:** On overflow-triggered compaction the ORIGINAL user message stays in storage; after the summary completes, a NEW user message is written carrying copies of its parts under fresh ids (media swapped for `[Attached …]` text so the same oversize payload can't re-overflow). Without replay (normal auto-compaction), an `autocontinue` gate consults plugins first (`experimental.compaction.autocontinue`, default enabled :500-517); if enabled it writes a SYNTHETIC continue user message whose text differs for the overflow case (explains attachments were dropped) and carries `metadata:{compaction_continue:true}` + `synthetic:true` — documented in-source as an UNSTABLE marker for provider plugins to distinguish machine continues from human prompts (:537-540). Repeat compactions sync `compactionPart.tail_start_id` when selection moved it (:461-466).
**Invariant:** Replay parts MUST be copied with new PartIDs/messageID — reusing ids would corrupt the original transcript. Media→text substitution is what makes overflow-recovery terminate; keeping binary attachments would loop overflow⇄compaction forever. The `compaction_continue` metadata marker is explicitly not a stable contract.
**Probe:** `packages/opencode/test/session/revert-compact.test.ts` covers revert×compact interplay at the session level; direct pin:
```bash
grep -n 'compaction_continue\|isMedia(part.mime)\|tail_start_id' packages/opencode/src/session/compaction.ts
```
expect :486,:497-ish,:540,:461,:464 hits (media substitution + marker + tail sync).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "buildPrompt previousSummary compaction", limit: 5 });
// resolves opencode.packages.core.src.session.compaction.buildPrompt (packages/core/src/session/compaction.ts:160-174)
// — the prompt builder imported at :23 and called :384; processCompaction's own Effect-fn closure is NOT
// a graph node (known Effect-gen class).
```

## Verdict
Adopt the pair-hiding chained-summary algorithm, clone-before-plugin-transform, new-id media-to-text replay, and the unstable compaction_continue marker contract; adapt prompt text and schema specifics; omit SessionV1 wire shapes.
