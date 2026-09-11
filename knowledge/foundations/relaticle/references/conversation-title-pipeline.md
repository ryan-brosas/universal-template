<!-- capsule-v2 -->
# Conversation title pipeline — provisional name, cheap side-agent, CAS guard against user renames

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How do you auto-name conversations from the opening message without ever clobbering a human's rename or spending a full model turn?

## Job + titler agent + sanitizer
**Path/Symbol:** `packages/Chat/src/Jobs/GenerateConversationTitle.php` (`handle` :50-88, `generate` :90-120, queue/attributes docblock :20-33); `Agents/ConversationTitler.php` (whole, 66L); `Support/TitleSanitizer.php` (`clean` :20-26, `generated` :36-44).
**Signature:** job `(conversationId, provisionalTitle, message, provider)` with `#[Timeout(30)] #[MaxExceptions(1)]`, `$afterCommit = true`; titler prompt returns structured `{has_topic: bool, title: string(≤60)}`.
**Data Shape:** conversation row carries the raw opener as provisional `title`; CAS update matches on `where('title', $provisionalTitle)`; telemetry breadcrumbs `title.superseded|title.no_topic|title.generation_failed|broadcast.dropped`.

### Decisive source
```php
// Compare-and-swap: a rename typed while the model was thinking is the
// user's explicit choice and must not be overwritten by a guess.
$applied = DB::table('agent_conversations')
    ->where('id', $this->conversationId)
    ->where('title', $this->provisionalTitle)
    ->update(['title' => $title, 'updated_at' => now()]);

if ($applied === 0) {
    ChatTelemetry::breadcrumb('title.superseded', ...);
    return;
}
try { broadcast(new ConversationTitleGenerated(...)); }
catch (Throwable $e) { ChatTelemetry::breadcrumb('broadcast.dropped', ...); } // client turn-end pull recovers
```
```php
// Matched as a `/u` character class rather than passed to trim(): trim()
// compares bytes, so a UTF-8 quote list also eats the trailing byte of any
// multibyte letter that shares one — "…ś" became invalid UTF-8.
$title = preg_replace('/^["\'`""„‟«»''‚‛\s]+|["\'`""„‟«»''‚‛\s]+$/u', '', $title);
```

**Flow:** first send stores the truncated opener as title and dispatches this job on the DEFAULT queue (deliberately NOT `chat`: those workers stream turns for up to two minutes; the title must land alongside the answer) → separate `ConversationTitler` agent pinned `#[UseCheapestModel] #[MaxTokens(64)] #[Temperature(0.2)]` with NO tools and NO conversation memory, so titling "can never trigger a CRM write" → structured output gates on `has_topic` (greetings/test strings keep the provisional name and a LATER substantive message retries titling; attempts stop after ~3 messages) → sanitizer strips bidi controls, "Title:" prefixes, wrapping quotes, trailing punctuation, caps at 60 (human renames get 200).
**Invariant:** Failure is never fatal — provider errors leave the conversation exactly as it was. The CAS precondition is the whole race story: if any code path changed the title meanwhile, the guess silently loses. Broadcast failure after a successful write is caught, never rethrown.
**Probe:** `tests/Feature/Chat/ConversationTitleGenerationTest.php` — provisional stored verbatim (:73-80), dispatched alongside first turn only (:82-99), never overwrites a mid-thinking rename (:141-157), keeps provisional when the provider throws (:159-175), multibyte byte-trim regression `'Zapytanie Klientaś'` survives intact (:198-215), renamed chats are never re-titled (:217-234), no-topic openers get a later chance then stop (:236-285).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "GenerateConversationTitle ConversationTitler TitleSanitizer has_topic superseded", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt provisional-title + CAS-overwrite whenever async generation races user edits. Adapt the cheapest-model pinning to your provider catalog; keep the structured-output topic gate — free-text titlers otherwise become the label verbatim. Omit Reverb specifics.
