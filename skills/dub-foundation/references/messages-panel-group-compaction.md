<!-- capsule-v2 -->
# Sender-group message compaction — how does a chat transcript tighten consecutive messages from the same sender without breaking the first-in-group spacing?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What is the exact grouping predicate and where is the negative margin applied?

## MessagesPanel grouped-message flag
**Path/Symbol:** `apps/web/ui/messages/messages-panel.tsx:167-169` (predicate), `218` + `472` (application); `message-markdown.tsx:26` (prose pairing).
**Signature:** `isGroupedWithPrevious = !isFirstFromSender && !isNewTime` → applied as `isGroupedWithPrevious && "-mt-1.5"` in BOTH the live-message branch and CampaignMessage.
**Data Shape:** boolean per rendered message row; pairs with `isFirstFromSender` (idx===0 or sender changed) and `isNewTime`.

### Decisive source
```tsx
// MessagesPanel loop
const isFirstFromSender = idx === 0 || !isMessageSameSender(message, messages[idx - 1]);
// Messages continuing a sender's group sit tighter together:
// trims the container's 8px gap down to 2px
const isGroupedWithPrevious = !isFirstFromSender && !isNewTime;
…
className={cn("…", isNew && "animate-scale-in-fade", isGroupedWithPrevious && "-mt-1.5")}
```

**Flow:** per-row compute → same-sender AND no time boundary → `-mt-1.5` pulls the row up (8px gap→2px) → otherwise default gap; the markdown body cooperates by collapsing paragraph margins (`prose-p:m-0 [&_p+p]:mt-2`) so multi-paragraph bubbles don't double-space inside grouped rows.
**Invariant:** the flag must be computed in the PARENT map (it needs `messages[idx-1]`) and threaded down as a prop — deriving it inside the child re-introduces index coupling; a new-time boundary resets grouping even between same-sender messages; the identical class string appears in both branches — changing one without the other splits live vs campaign rendering.
**Probe:** `grep -c 'isGroupedWithPrevious' apps/web/ui/messages/messages-panel.tsx` → **6**; `grep -n '\-mt-1.5' apps/web/ui/messages/messages-panel.tsx` → lines 218 and 472.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "MessageMarkdown MessagesPanel", limit: 5 });
```

## Verdict
Adopt the parent-computed grouping flag + single negative-margin token + prose `[&_p+p]:mt-2` pairing for chat transcripts; adapt spacing values to your scale; omit the animate-scale-in-fade coupling if you have no new-message animation.
