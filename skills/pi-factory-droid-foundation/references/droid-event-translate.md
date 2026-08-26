<!-- capsule-v2 -->
# Droid event translation — how do I map a foreign delta stream onto host content blocks without duplicates or dangling blocks?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When a remote agent emits keyed text/thinking deltas plus usage and result events, how do I fold them into host assistant-message blocks so every block is created once, closed exactly once, and errors propagate?

## Keyed block dedup + open-key closing
**Path/Symbol:** `src/providers.ts:translate` (872-932), `closeOpenBlocks` (1150-1173).
**Signature:** `function translate(event: DroidMessage, output: AssistantMessage, stream: AssistantMessageEventStream, indexOf: Map<string, number>, openTextKeys: Set<string>, openThinkingKeys: Set<string>, model: Model<Api>, usage: UsageTracker): void`
**Data Shape:** `indexOf: Map<"text|think:messageId:blockIndex", number>` maps event keys to `output.content` indices; the two open-key sets track blocks that have started but not ended.

### Decisive source
```ts
case DroidMessageType.AssistantTextDelta: {
  const key = `text:${event.messageId}:${event.blockIndex}`;
  let index = indexOf.get(key);
  if (index === undefined) {
    index = output.content.length;
    output.content.push({ type: "text", text: "" });
    indexOf.set(key, index);
    openTextKeys.add(key);
    stream.push({ type: "text_start", contentIndex: index, partial: output });
  }
  const block = output.content[index];
  if (block?.type !== "text") return;
  block.text += event.text;
  stream.push({ type: "text_delta", contentIndex: index, delta: event.text, partial: output });
  return;
}
```

Usage + failure events:
```ts
case DroidMessageType.TokenUsageUpdate:
  // Streamed values are session-cumulative. Convert to per-turn deltas so
  // Pi footer/context math stays sane mid-turn.
  usage.applyTurnUsage(output, usage.cumulativeToTurnBuckets(event), model, { preferLastCall: false });
  return;
case DroidMessageType.Result:
  if (event.tokenUsage) {
    usage.applyTurnUsage(output, usage.cumulativeToTurnBuckets(event.tokenUsage), model, { preferLastCall: false });
  }
  if (event.isError) throw new Error(event.errors?.join("; ") || event.error?.message || "Droid execution failed");
```

End-of-turn close (called after the stream loop, before done):
```ts
for (const key of openTextKeys) {
  const index = indexOf.get(key);
  const block = ...;
  if (index !== undefined && block?.type === "text") {
    stream.push({ type: "text_end", contentIndex: index, content: block.text, partial: output });
  }
}
openTextKeys.clear(); // same for thinking keys with thinking_end
```

**Flow:** per delta → key by messageId:blockIndex → create block + start event on first sight → append + delta event on every sight → TokenUsageUpdate/Result convert cumulative→turn buckets mid-stream → Result.isError or Error events THROW out of translate into the caller's catch (which emits error + end) → after loop, closeOpenBlocks emits one end event per still-open block.
**Invariant:** One content block per `(messageId, blockIndex)`; every started block gets exactly one end event even when the remote never sends an explicit close; unknown event types are ignored (Droid owns its internal tool loop — Pi receives only assistant text/thinking); a failed result must not be swallowed as a normal stop.
**Probe:** No dedicated upstream unit suite for `translate`/`closeOpenBlocks` (they need the SDK event enums); recorded caveat. Deterministic pins: key construction at `src/providers.ts:884` and `:900`; default-ignore comment at `:928-930`. The pure usage half of translate IS directly tested in `test/usage.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "translate closeOpenBlocks AssistantTextDelta ThinkingTextDelta", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the composite-key block registry with lazy creation, the open-set/end-event pairing, mid-stream usage conversion, and throw-on-error-result. Adapt event type names and block shapes to your host's message model. Omit the Droid-specific rule that tool activity stays invisible to the host.
