<!-- capsule-v2 -->
# Thread observer denormalization — how does the conversation row stay consistent without a transaction across thread writes?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** Which conversation fields are derived from threads, and what exact predicate decides each update when a new thread is created?

## ThreadObserver::created
**Path/Symbol:** `app/Observers/ThreadObserver.php:17` (`created`, 17–96).
**Signature:** `public function created(Thread $thread)` — fires on EVERY thread insert (customer email, agent reply, note, lineitem).
**Data Shape:** mutates in-memory `$conversation` then `$conversation->save()`; uses `config('app.use_mail_date_on_fetching')` to pick "now" (thread's created_at vs wall clock) exactly like FetchEmails.

### Decisive source
```php
// app/Observers/ThreadObserver.php:33-63 (abridged)
if (!in_array($thread->type, [TYPE_LINEITEM, TYPE_NOTE]) && $thread->state == STATE_PUBLISHED) {
    $conversation->threads_count++;                       // only customer+message threads count
}
if (!in_array($thread->type, [TYPE_CUSTOMER])) {
    $conversation->user_updated_at = $now;                // agent activity marker
}
if ((in_array($thread->type, [TYPE_CUSTOMER, TYPE_MESSAGE])
        || ($conversation->isPhone() && in_array($thread->type, [TYPE_NOTE]))
        || ($conversation->threads_count == 0 && $thread->type == TYPE_NOTE))
    && $thread->state == STATE_PUBLISHED) {
    $conversation->setLastReplyAt($now, $thread->source_via);
    $conversation->last_reply_from = $thread->source_via; // may already be set by FetchEmails — same value
}
if ($conversation->source_via == PERSON_CUSTOMER) { $conversation->read_by_user = false; }
```
Preview rule (:65-73): types CUSTOMER/MESSAGE/NOTE published and NOT a forward (`$thread->isForward()`) ⇒ `$conversation->setPreview($thread->body)`.
Realtime refresh (:85-90): only TYPE_CUSTOMER threads or DRAFT-state user messages trigger `Conversation::refreshConversations`.

**Flow:** every path ends with `$conversation->save()`; Eventy `thread.created` fires last. ConversationObserver adds guards on its own lifecycle: subject truncated to SUBJECT_MAXLENGTH on BOTH creating and updating (:5201), `read_by_user = true` when source_via is USER, `deleting` cascades threads+followers then fires `conversation.deleting`.
**Invariant:** type gates are EXCLUSION lists, not inclusion lists — adding a new thread type silently inherits threads_count/user_updated_at behavior unless explicitly excluded. Notes never bump `threads_count` but DO set preview and can seed `setLastReplyAt` for phone conversations or zero-thread conversations (#5105). This observer is why FetchEmails sets some conversation fields BEFORE saving the thread and lets the observer re-save after — double-write by design, not an accident.
**Probe:** `grep -c "STATE_PUBLISHED" app/Observers/ThreadObserver.php` (= 5 — 3 live + 2 commented-out lines).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "ThreadObserver created conversation", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the exclusion-list predicates + preview/realtime gates as the portable denormalization contract; adapt Eloquent observers to your ORM's hooks keeping the "observer recomputes, command pre-sets" pairing; omit the phone/note special cases if you have no chat/phone channels. Direct tests: none upstream target the observer directly.
