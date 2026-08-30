<!-- capsule-v2 -->
# Side-panel transcript lifecycle — how can an embedded chat switch conversations without losing page context or deleting another user's transcript?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5dcc97765fcba6fdf62585c541e1b`; direct source/test read (Codebase Memory MCP unavailable this session). **Question:** What state transitions should a tenant-aware chat side panel expose when opening, refreshing context, starting, rendering, and deleting conversations?

## Keep page binding separate from transcript selection and delegate destructive ownership checks
**Path/Symbol:** `packages/Chat/src/Livewire/App/Chat/ChatSidePanel.php:mount/openPanel/refreshContext/openConversation/startNewConversation/deleteConversation/render` (:53-172); `packages/Chat/src/Actions/DeleteConversation.php:execute` (:10-35).
**Signature:** `refreshContext(?string $url = null): void`; `openConversation(string $conversationId): void`; `startNewConversation(): void`; `deleteConversation(string $conversationId): void`; `render(): View`.
**Data Shape:** Public state consists of `isOpen`, nullable `conversationId`, nullable page-record `(recordType, recordId, recordName)`, and `starterPrompts`. `refreshContext` replaces only record fields/prompts and dispatches `chat:context-updated`; opening or starting a transcript changes only `conversationId`. Rendering returns null URLs when Filament has no tenant. Deletion is a transaction over conversation, messages, and pending actions, scoped to the current user's morph identity and current team.

### Decisive source
```php
public function startNewConversation(): void
{
    $this->conversationId = null;
}
```
```php
$deleted = DB::table('agent_conversations')
    ->where('id', $conversationId)
    ->where('participant_type', $user->getMorphClass())
    ->where('participant_id', $user->getKey())
    ->where('team_id', $user->current_team_id)
    ->delete();

if ($deleted === 0) {
    return false;
}
```

**Flow:** `mount()` refreshes page context immediately, even while the panel is closed, so opening does not require a navigation round-trip. `openPanel` toggles visibility and optionally selects a conversation; `closePanel` and `togglePanel` do not disturb context or transcript. `refreshContext` resolves a supplied URL through the context service, updates starter prompts, and emits a browser event. `openConversation` swaps the embedded transcript; `startNewConversation` clears only that id, deliberately preserving record context. `deleteConversation` first requires an authenticated `User`, delegates to an ownership/team-scoped transaction, clears the selected id only when the deleted id was open, and emits a deletion event. `render` hides full-page links on tenant-less pages and otherwise supplies a placeholder URL for a client-side conversation-id swap.
**Invariant:** Transcript selection is orthogonal to page context. A new chat does not forget the record the user is viewing, and deleting a different transcript does not reset the open one. Foreign-user or foreign-team conversation ids are silent no-ops: no rows, messages, pending actions, or browser events are changed. Tenant-less pages remain renderable instead of attempting tenant-bound route generation.
**Probe:** `tests/Feature/Chat/ChatSidePanelContextTest.php` (:16-86) pins context refresh while closed, stale-context clearing, cross-team refusal, event dispatch, and starter prompts; `tests/Feature/Chat/ChatSidePanelConversationsTest.php` (:32-102) pins transcript switching, fresh starts, ownership-safe deletion, tenant-less rendering, and no credit footer; `tests/Feature/Chat/LazyConversationLoadTest.php` (:16-32) pins prompt assembly independent of panel state. Browser smoke: `tests/Browser/Chat/SidePanelTest.php` (:8-15).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ChatSidePanel refreshContext openConversation startNewConversation DeleteConversation tenant-less", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt separate state machines for panel visibility, page-record binding, and transcript selection; make destructive deletion a transaction with both participant and tenant predicates; and make tenant-less rendering an explicit supported state. Adapt Livewire events, route URL placeholders, and persistence tables. The URL-to-record trust boundary itself is covered by `chat-page-context-url-binding.md`; this capsule covers the distinct transcript lifecycle and rendering/deletion behavior.
