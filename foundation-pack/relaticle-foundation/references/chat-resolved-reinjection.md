<!-- capsule-v2 -->
# Resolved-proposal re-injection — every turn replays outcomes the transcript still calls pending

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you keep a tool-calling agent from believing an approved/rejected proposal is still awaiting action?

## resolvedForConversation() + summarizeSuperseded()
**Path/Symbol:** `packages/Chat/src/Services/PendingActionService.php`: `resolvedForConversation()` (:464-500) + docblock (:464-471); consumer wiring in `ProcessChatMessage.handle()` (:154-156); supersede summaries (:459-483).
**Signature:** `resolvedForConversation(string $conversationId): list<{operation, entity_type, status, label, record_id, record_ids}>`
**Data Shape:** Terminal statuses: Approved|Rejected|Expired|Superseded with resolved_at NOT NULL; newest-20 by resolved_at then id desc, REVERSED to oldest-first before return.

### Decisive source
```php
// Deliberately NOT windowed to "since the last assistant turn": resolutions write
// nothing into the replayed transcript, whose tool results keep claiming the proposal
// is pending — so the outcome must be re-injected on every turn or the model treats
// a rejected proposal as still awaiting approval.
```

**Flow:** each new job run collects terminal proposals (labels via display_data.name/title → action_data fallback; record ids from result_data) plus summaries of just-superseded ones → both handed to the agent BEFORE streaming (`withResolvedActions` / `withSupersededProposals`) → the model's view of state no longer depends on stale in-transcript tool results.
**Invariant:** Re-injection is UNCONDITIONAL per turn — windowing by recency is the bug this exists to prevent; ordering must be oldest-first so the narrative reads chronologically.
**Probe:** `tests/Feature/Chat/BatchResolvedActionsTest.php`, `ResolvedActionsContextTest.php`, `CrmAssistantResolvedBlockTest.php`, `ProposalRetryIdempotencyTest.php`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "resolvedForConversation withResolvedActions summarizeSuperseded", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt explicit out-of-band state re-injection for any agent whose side effects live outside its transcript. Adapt payload fields. Omit UI card rendering. Direct tests cover the batch and context planes.
