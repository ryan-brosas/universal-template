<!-- capsule-v2 -->
# Conversation state write-in ladder — how does an inbound email mutate conversation status, customer, CC, and folders without corrupting them?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** When a customer email lands, which conversation fields change, in what order, and which traps (spam freeze, deleted revive, attachment flag monotonicity) must a porter preserve?

## saveCustomerThread
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:1169` (`saveCustomerThread`, 1169–1352).
**Signature:** `public function saveCustomerThread($mailbox, $message_id, $prev_thread, $from, $to, $cc, $bcc, $subject, $body, $attachments, $headers, $date)` → returns the saved `Thread`.
**Data Shape:** `$now = use_mail_date_on_fetching ? $date : now()` — imported mail can carry its original Date header; `Customer::create($from)` upserts by sanitized email.

### Decisive source
```php
// app/Console/Commands/FetchEmails.php:1238-1252
$conversation->customer_email = $from;
// Reply from customer makes conversation active.
// If conversation is marked as Spam the status does not change.   (#5005)
if (!$conversation->isActive() && !$conversation->isSpam()) {
    $conversation->status = \Eventy::filter('conversation.status_changing', Conversation::STATUS_ACTIVE, $conversation);
}
$conversation->setLastReplyAt($now, Conversation::PERSON_CUSTOMER);
$conversation->last_reply_from = Conversation::PERSON_CUSTOMER;
// Reply from customer to deleted conversation should undelete it.
if ($conversation->state == Conversation::STATE_DELETED) {
    $conversation->state = Conversation::STATE_PUBLISHED;
}
$conversation->updateFolder();
```
Attachment-flag monotonicity (:1222-1228): `has_attachments` is set true only when the NEW email has attachments AND it was previously false — a reply WITHOUT attachments never writes 0 back. BCC preservation (:1232-1236): `$conversation->setBcc($bcc)` runs only when the incoming bcc list is non-empty, so the first email's BCC survives replies.

**Flow:** existing prev_thread ⇒ same conversation; different sender ⇒ swap `customer_id`, demote original to CC (skipping emails already in Bcc array), fire `ConversationCustomerChanged` AFTER events (:1191-1204, :1336-1338). New ⇒ build conversation with TYPE_EMAIL/STATE_PUBLISHED/preview from body (:1206-1220). Thread row mirrors type=TYPE_CUSTOMER, status=$conversation->status, source_via/source_type=CUSTOMER/EMAIL; on thread-save exception a NEW conversation is deleted forever before rethrowing (#3186, :1278-1287). Then attachments → cid→URL rewrite (`replaceCidsWithAttachmentUrls`) → base64-image replacement → second save only if body changed (:1289-1313). Folder counters refresh + domain events close the flow (:1324-1333).

## updateFolder — folder placement predicate
**Path/Symbol:** `app/Conversation.php:984-1017`.
```php
if      ($this->state == self::STATE_DRAFT)   { $folder_type = Folder::TYPE_DRAFTS; }
elseif ($this->state == self::STATE_DELETED)  { $folder_type = Folder::TYPE_DELETED; }
elseif ($this->isSpam())                      { $folder_type = Folder::TYPE_SPAM; }
elseif ($this->isClosed())                    { $folder_type = Folder::TYPE_CLOSED; }
elseif ($this->user_id)                       { $folder_type = Folder::TYPE_ASSIGNED; }
else                                          { $folder_type = Folder::TYPE_UNASSIGNED; }
```
**Invariant:** strict precedence draft > deleted > spam > closed > assigned > unassigned; the folder row is looked up per mailbox and ONLY `$folder_id` changes — counters update separately via `Mailbox::updateFoldersCounters()`.

## setLastReplyAt — waiting-since semantics switch
**Path/Symbol:** `app/Conversation.php:501-521`.
With `app.waiting_since_as_first_unanswered_customer_message` ON, `last_reply_at` moves only when the PREVIOUS `last_reply_from != PERSON_CUSTOMER` (first unanswered customer message), while `last_customer_reply_at` ALWAYS tracks the latest customer reply (#5225). PORTER TRAP: docstring says "$this->last_reply_from MUST store previous value" — call sites must set `last_reply_from` AFTER calling this, and the method contains an inert bug (`$date->format` on non-Carbon path guarded by `isCarbon`) that must not be cargo-culted.
**Probe:** `grep -c "isSpam()" app/Conversation.php` (= 2 — definition :580 + updateFolder arm :990) and `grep -c "'conv_view'" app/Conversation.php` (= 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "conversation status folder update", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the field-mutation order (status guard → reply timestamps → undelete → folder), spam-freeze, monotonic has_attachments, and BCC-preservation rules; adapt Eventy filter points to your hook system; omit Laravel observer coupling if you compute counts directly. Direct tests: tests/Feature/ConversationChangeCustomerTest.php covers the customer-swap arm end-to-end.
