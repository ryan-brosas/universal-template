<!-- capsule-v2 -->
# Messaging read-path scrollers — how do I page conversations AND per-conversation messages with the SAME timestamp-cursor machine?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** How do thin scroller subclasses parameterize an abstract cursor machine for two different entities — and which field name must each supply?

## Two subclasses, one machine
**Path/Symbol:** `src/scrollers/conversation.scroller.ts:ConversationScroller` (:10–44); `src/scrollers/message.scroller.ts:MessageScroller` (:9–41); wire layer `src/requests/conversation.request.ts:getConversations/getConversation`.
**Signature:** `class ConversationScroller extends CreatedBeforeScroller<Conversation>` with `fieldName: 'lastActivityAt'`; `class MessageScroller extends CreatedBeforeScroller<MessageEvent>` with `fieldName: 'createdAt'`; both take a bound fetch closure + context (`recipients`, `conversationId`) and override only `fetch()`.
**Data Shape:** fetch closures return `Promise<Conversation[] | MessageEvent[]>`; optional filters spread ONLY when defined (`...(isUndefined(this.createdBefore) ? {} : { createdBefore: new Date(this.createdBefore) })`).

### Decisive source
```ts
export class ConversationScroller extends CreatedBeforeScroller<Conversation> {
  fieldName: 'lastActivityAt' = 'lastActivityAt';
  async fetch(): Promise<Conversation[]> {
    return this.fetchConversations({
      ...(isUndefined(this.createdBefore) ? {} : { createdBefore: new Date(this.createdBefore) }),
      ...(this.recipients && { recipients: this.recipients }),
    });
  }
}
```

Wire twin (`conversation.request.ts`): GET `messaging/conversations` with `{ keyVersion: 'LEGACY_INBOX', q: 'participants', recipients: castArray(recipients), createdBefore: createdBefore.getTime() }` — each param present ONLY when its filter is set; single-fetch twin adds `keyVersion: 'LEGACY_INBOX'` to `messaging/conversations/{id}`.
**Flow:** subclass binds context at construction (recipients filter or conversationId scope) → base machine drives paging via the overridden `fieldName`: seed = `results[0][fieldName] + 1000`, cursor advance = last element's `fieldName` (see created-before-scroller). The entity's timestamp FIELD NAME is the entire per-entity contract.
**Invariant:** `fieldName` MUST match the actual timestamp key on the hydrated entity — conversations order by `lastActivityAt`, messages by `createdAt`; swapping them silently pages by undefined. The conditional-spread idiom keeps absent filters off the wire entirely (no `undefined` params). `recipients` accepts scalar-or-array; the request layer normalizes with `castArray`. Read side uses `keyVersion: 'LEGACY_INBOX'` on BOTH endpoints — same constant as the write path (messaging-write-path-duality) but a different concern: it selects the legacy inbox projection for reads.
**Probe:** `test/message/message-repository.spec.ts` scrollBack block (:200–259) pins MessageScroller paging math; conversation twin `test/conversation/conversation-repository.spec.ts` (:231–252) pins the `lastActivityAt` variant; check_index_coverage on all four cited paths = no_recorded_issue.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "ConversationScroller MessageScroller fieldName", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bind-context-at-construction + declare-cursor-field subclass shape for ANY timestamp-keyed feed. Adapt field names to your entity schema. Omit the LEGACY_INBOX literal (endpoint-specific). Direct tests pin both variants.
