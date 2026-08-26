<!-- capsule-v2 -->
# whatsapp-no-edit-capability-fallbacks

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-whatsapp/src/adapter.ts`
- Symbol: `WhatsAppAdapter.update / stream / delete / sendText / recordOutbound`
- Lines: update :129-133, stream :135-143, delete :145-147, sendText :221-241, recordOutbound :249-263
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-whatsapp.src.adapter.WhatsAppAdapter.recordOutbound`

## Question
When a channel has NO edit, NO delete, and NO streaming APIs, how do the shared engine contracts (update/stream/delete + quote-reply history) degrade without lying to the engine?

## Signature & Data Shape
```typescript
async update(ref, ir): Promise<void>;   // posts a FRESH message — WhatsApp cannot edit
async stream(target, chunks): Promise<MessageRef>;  // buffers the WHOLE iterable, sends once
async delete(_ref): Promise<void>;      // silent no-op — business messages can't be deleted
sendText(to, text): Promise<WhatsAppMessageRef>;    // markdown→WA formatting + ≤4096 split
recordOutbound(to, text, ref): void;    // fire-and-forget history append keyed by wamid
```

## Decisive Source Excerpt
```typescript
// WhatsApp can't edit messages; "update" posts a fresh message instead.
const r = ref as unknown as WhatsAppMessageRef;
await this.post({ to: r.to, phoneNumberId: r.phoneNumberId }, ir);
...
// Record an outbound message in history keyed by its WhatsApp id, so a later
// quote-reply to it (the webhook sends only the quoted id) resolves to this text.
if (!ref.id || !text) return;
void this.history.append(conversationKeyOf(to), { role: "assistant", content: text,
  ts: `${Date.now()}`, id: ref.id }).catch(() => {});
```

## Flow
1. `capabilities = { supportsStreaming: false, … }` is declared honestly; the engine's `stream()` contract still works but degrades to buffer-everything-send-once.
2. `update()` re-posts as a new message (the engine's in-place edit expectation collapses to "the latest message reflects current state"); `delete()` no-ops rather than throwing.
3. Outbound text goes through `markdownToWhatsApp` then `splitForWhatsApp(body, WA_LIMITS.bodyText=4096)`; every posted part is recorded in local history under its platform message id.
4. The history ledger exists because a quote-reply webhook carries ONLY the quoted wamid — resolving it back to text requires the adapter to have journaled its own outbound traffic; journal failures are swallowed so history can never break a send.
5. Media posting uploads bytes first (`uploadMedia`) then references the media id; images ride as `image` payloads with caption, everything else as `document`.

## Invariant
Capability gaps are bridged by honest degradation (re-post/no-op/buffer), never by throwing or pretending success with stale ids; outbound self-journaling keyed by platform ids is what keeps quote-replies resolvable.

## Direct-Test Probe
- File: `packages/channels-whatsapp/src/adapter.test.ts` (stream/update degradation paths)
- Also `packages/channels-whatsapp/src/render/message.test.ts` :85 clamps button titles to 20 chars; :108 numbered text menu fallback beyond 10 options; :122 THROWS when an encoded button value exceeds the 256-char control-id limit

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"WhatsAppAdapter recordOutbound splitForWhatsApp sendText","limit":10}'
```

## Verdict
Adopt honest-degradation mapping plus the wamid-keyed outbound journal for any constrained channel. Adapt limits/formatting per host (`WA_LIMITS`: bodyText 4096, replyButtons 3, buttonTitle 20, interactiveBody 1024, listRows 10, controlId 256). Note the deliberate asymmetry: rendering CLAMPS display strings but LOUDLY THROWS when a routing value cannot fit — data loss beats silent misrouting.
