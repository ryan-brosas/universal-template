<!-- capsule-v2 -->
# Messaging write-path duality — one endpoint, two payload shapes for send-into-conversation vs create-with-recipients (how do I send DMs via the private API)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** What are the exact voyager payloads to send a message, and how does "reply in existing conversation" differ from "start a new thread"?

## The twin payloads
**Path/Symbol:** `src/requests/message.request.ts:sendMessage` (:15–58); repository wrapper `src/repositories/message.repository.ts:sendMessage` (:28–40).
**Signature:** `sendMessage({profileId?, conversationId?, text})` → POST `?action=create`; with `conversationId` ⇒ POST `messaging/conversations/{id}/events`, without ⇒ POST `messaging/conversations`.
**Data Shape:** both bodies nest a typed value object `'com.linkedin.voyager.messaging.create.MessageCreate'` holding `attributedBody: {text, attributes: []}`; the DIRECT variant wraps it in `conversationCreate.eventCreate` + `subtype: 'MEMBER_TO_MEMBER'` + `recipients: [profileId]` + top-level `keyVersion: 'LEGACY_INBOX'`; the CONVERSATION variant adds an `originToken` UUID and `dedupeByClientGeneratedToken: false`.

### Decisive source
```ts
const directMessagePayload = {
  keyVersion: 'LEGACY_INBOX',
  conversationCreate: {
    eventCreate: { value: { 'com.linkedin.voyager.messaging.create.MessageCreate': {
      attributedBody: { text, attributes: [] }, attachments: [] } } },
    subtype: 'MEMBER_TO_MEMBER',
    recipients: [profileId],
  },
};
const conversationPayload = {
  eventCreate: {
    originToken: '54b3a724-59c5-4cf2-adbd-660483010a87',
    value: { 'com.linkedin.voyager.messaging.create.MessageCreate': {...} },
  },
  dedupeByClientGeneratedToken: false,
};
const url = conversationId ? `messaging/conversations/${conversationId}/events` : 'messaging/conversations';
```

**Flow:** branch on `conversationId` presence — that single field selects URL AND body shape. Response `{data.value}` is spread into the returned event object with the local `text` re-attached (repository :39) because the server echo omits it. Read side is symmetric: GET same `/events` path with `keyVersion: 'LEGACY_INBOX'` + optional `createdBefore` ms (feeds CreatedBeforeScroller).
**Invariant:** the typed-key object (`com.linkedin.voyager...MessageCreate`) is REQUIRED verbatim — flattening it breaks the request; `attributes: []` must exist even when empty; the hardcoded originToken works but should be regenerated per port (it's a client-generated idempotency-ish token, not a secret). Reads and writes share ONE path namespace (`messaging/conversations[/{id}][/events]`) with `action: 'create'` as query param.
**Probe:** `test/message/message-repository.spec.ts:262–311` pins the full direct-payload POST (stub matches exact body + `{params: {action: 'create'}}`, response `{data: {value}}` echoed back with text attached).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "sendMessage MessageCreate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the branch-on-context-id pattern (existing-thread id → events subpath + minimal body; no id → create endpoint + recipient envelope) for ANY messaging API. Adapt the typed keys/keyVersion per API generation. Contrast in-suite: linvo's browser-side sends (message-send-guard-chain) solve the same problem over DOM — this is the headless-API counterpart; pair them when choosing an integration lane.
