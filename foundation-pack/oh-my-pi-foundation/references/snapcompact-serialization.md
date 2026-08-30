<!-- capsule-v2 -->
# Snapcompact serialization — turning conversation history into a renderable text transcript

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How does a porter serialize a message list into the `¶user:`/`¶think:`/`¶ai:`/`¶call:` transcript that the frame renderer prints, without losing the tool-result/tool-call pairing or the intent that keeps the archive legible?

## Serialization
**Path/Symbol:** `packages/snapcompact/src/snapcompact.ts:serializeConversation` (928–1059), `truncateForSummary` (773–781), `elideDataUrls` (858–907), `stripDimMarkers` (924–926).
**Signature:** `serializeConversation(messages: Message[], options?: SerializeOptions): string`.
**Data Shape:** `SerializeOptions = { toolResultMaxChars?=2000, toolArgMaxChars?=500, toolCallMaxChars?=2000, truncateHeadRatio?=0.6, dimToolResults?=true, includeThinking?=true }`. Output is a `¶`-prefixed section transcript joined by `\n\n`.

### Decisive source
```ts
// Tool results flagged contextually useless (and their paired calls) carry no
// information worth archiving — skip the whole pair.
const uselessCallIds = new Set<string>();
const resultTextByCallId = new Map<string, string>();
for (const msg of messages) {
  if (msg.role !== "toolResult") continue;
  if (msg.useless === true && msg.isError !== true) { uselessCallIds.add(msg.toolCallId); continue; }
  const text = msg.content.filter(b => b.type === "text").map(b => b.text).join("");
  if (text) resultTextByCallId.set(msg.toolCallId, text);
}
// ... in the assistant loop, each toolCall block:
const resultText = resultTextByCallId.get(block.id);
if (resultText !== undefined) { mergedCallIds.add(block.id); lines.push(renderResultBlock(resultText)); }
```
Tool results are merged INTO their originating `¶call:` block (indexed by tool-call id), so a call and its result render as one scope. Useless results (and their paired calls) are skipped entirely. `renderResultBlock` wraps the body in `<out>…</out>` and dims only the body (`DIM_ON`/`DIM_OFF` zero-width toggles) so frame coloring keeps scope markers and calls loud. Tool-call args render as `name(args)//intent`, dropping the harness `INTENT_FIELD` from the args and lifting it to a one-line comment. `includeThinking` defaults true but must be set false for Anthropic-dialect readers (replayed `¶think:` trips the `reasoning_extraction` classifier — issue #6093).

**Flow:** pre-scan toolResults → build `resultTextByCallId` + `uselessCallIds` → walk messages: user → `¶user:`, assistant → buffer thinking/text then flush `¶think:`/`¶ai:` before each toolCall → `¶call:name(args)//intent` + merged `<out>` result → orphan toolResults render standalone. `pushPart` coalesces consecutive same-prefix sections with a smart newline.

**Invariant:** a tool result is never archived standalone when its call is in the window — it merges into the call block, so the archive reads as coherent scopes, not interleaved fragments. `elideDataUrls` runs before truncation so a character cap can never slice inside a base64 payload (which would replay as broken image input on every later request).

**Probe:** `packages/snapcompact/test/snapcompact.test.ts:646` ("serializeConversation" — asserts the `¶user:`/`¶call:name(args)//intent` shapes and `<out>` dimming); `:1321` ("data URL elision" — a cut landing on `;base64,` still matches and collapses to `[data URL omitted: …]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "serializeConversation renderResultBlock truncateForSummary", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the merge-result-into-call-scope invariant, the useless-result pair skip, and the intent-as-comment lift — a porter who emits tool results as standalone messages loses the pairing that makes the archive readable and the dim-ink coloring that keeps calls loud. Adapt the `¶` prefixes and the exact truncation budgets. Omit the harness-specific `INTENT_FIELD` plumbing if your tool-call schema differs. Coverage: `no_recorded_issue` + `metadata_match` on the `oh-my-pi` full index.
