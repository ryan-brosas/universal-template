<!-- capsule-v2 -->
# Conversation move & forward lineage — how do you relocate a ticket across mailboxes and spawn forwarded copies without breaking threading or signatures?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How is a conversation moved between mailboxes recorded, and how does the forward-child thread pull in parent replies at send time?

## Move plane + meta lineage keys
**Path/Symbol:** `app/Conversation.php` (move helpers + `ACTION_TYPE_MOVED_FROM_MAILBOX = 3`, Thread.php:114); forward metas `META_FORWARD_PARENT_CONVERSATION_NUMBER/ID`, `META_FORWARD_PARENT_THREAD_ID` (+ child twins) Thread.php:164-168; backward-compat rename map `$meta_fw_backward_compat` :171-177.
**Signature:** `Thread::getMetaFw($key, $default)` (Thread.php:1341) reads through the compat map; `isForwarded()` :1392; `getForwardParentConversation()` :1412.
**Data Shape:** lineitem thread with `action_type=MOVED_FROM_MAILBOX` and `action_data=<new mailbox_id>` records the move INSIDE the timeline; forward child stores parent pointers in JSON `meta`.

### Decisive source
```php
// app/Jobs/SendReplyToCustomer.php:85-119 — forwarding pulls parent replies into the child email
if ($this->conversation->threads_count == 1 && count($this->threads) == 1) {
    $forward_child_thread = $this->threads[0];
    if ($forward_child_thread->isForwarded() && $forward_child_thread->getForwardParentConversation()) {
        $forwarded_replies = $forward_child_thread->getForwardParentConversation()
            ->getThreads(null, null, [TYPE_CUSTOMER, TYPE_MESSAGE, TYPE_LINEITEM]);
        ...
        foreach ($forwarded_replies as $i => $thread) {
            if ($thread->created_at > $forward_parent_thread->created_at) {
                $forwarded_replies->forget($i);        // nothing created after the fork
            }
        }
        $this->threads = $this->threads->merge($forwarded_replies);
```
Signature correctness during moves (:104-115): while merging, each reply whose mailbox CHANGED gets `mailbox_change_history[reply_id] = <mailbox id from its MOVED_FROM_MAILBOX lineitem>` so the rendered signature matches the mailbox that owned the conversation AT REPLY TIME.
**Flow:** move = change mailbox_id + append MOVED lineitem + refold folders/counters; undo of forward deletes the child (job early-returns when `!$this->conversation` :72-75). History policy interplay: forced-forward conversations always render FULL history even when global setting is none/global (:244-250).
**Invariant:** forward-merge window is `[conversation start .. forward_parent_thread.created_at]` — replies on the parent AFTER forwarding must not leak into the child's email; sortThreads (desc created_at, tiebreak id desc — Thread.php:1563-1584 with issue #2938 rationale) runs BEFORE slicing so "first two" means newest. Meta keys were renamed once; readers MUST go through getMetaFw to accept old rows.
**Probe:** `grep -c "getForwardParentConversation()" app/Jobs/SendReplyToCustomer.php` (= 2) and `grep -c "META_FORWARD_PARENT_THREAD_ID" app/Jobs/SendReplyToCustomer.php` (= 1) — probe terms individually, never as one alternation (line-count trap).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "forward parent conversation threads", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt meta-pointer lineage + time-boxed reply inheritance + per-reply signature history as the portable move/forward contract; adapt the JSON meta bag to your schema; omit lineitem rendering specifics if your UI differs — but keep recording moves as first-class timeline rows. Direct tests: none upstream for this seam.
