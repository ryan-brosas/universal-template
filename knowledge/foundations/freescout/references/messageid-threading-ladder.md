<!-- capsule-v2 -->
# Message-ID identity & threading ladder — how do you decide which conversation an inbound email belongs to?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** Given an inbound email, how does the fetcher resolve (a) duplicate detection, (b) the previous thread, and (c) whether the sender is a customer or an agent — when mail providers rewrite Message-IDs?

## processMessage resolution order
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:383` (`processMessage`, 383–1060).
**Signature:** `public function processMessage($message, $message_id, $mailbox, $mailboxes, $extra = false)`.
**Data Shape:** `$message` = Webklex Message; `$message_id` = header value (may be empty); `$prev_message_ids` = ordered candidate list; Thread lookup keyed on `threads.message_id`.

### Decisive source
```php
// app/Console/Commands/FetchEmails.php:497-538 — candidate assembly, weakest-first
$in_reply_to = trim($message->getInReplyTo() ?? '', '<>');
$references = $message->getReferences();
...
if ($in_reply_to) { $prev_message_ids[] = $in_reply_to; }
if ($references) { foreach ($references as $reference) { ... $prev_message_ids[] = trim($reference); } }
// Providers may rewrite outgoing Message-IDs, so the body marker is a fallback:
$html_body = $message->getHTMLBody(false);
$marker_message_id = \MailHelper::fetchMessageMarkerValue($html_body);   // '{#FS:<base64>#}'
if ($marker_message_id) { $prev_message_ids[] = $marker_message_id; }
// :615-621 — ALSO append the artificial 'fs-<md5>@' variants of every candidate
foreach ($prev_message_ids as $prev_message_id) {
    $new_prev_message_id = \MailHelper::generateMessageId($prev_message_id, $mailbox->id.$prev_message_id);
    ...
}
```

**Flow:** ① sender = Reply-To unless missing/`@unknown`, else From (:388-419). ② empty Message-ID ⇒ generate `fs-<md5(raw body)>@<domain>` (:423-427). ③ Jira hack: collapse `JIRA.<n>.<ms>@Atlassian.JIRA` to its stem so ticket follow-ups thread (#2927, :431-445). ④ dedupe: existing `Thread.message_id` normally means "already fetched → setSeen + return"; BUT if this mailbox is not the stored one AND the stored id looks like an outbound FS id (`MailHelper::isFsMessageId`), flip to `$extra = true` and re-import into this mailbox under a per-mailbox artificial id `generateMessageId($from|$id, $mailbox->id.$id)` (:451-482). ⑤ walk `$prev_message_ids` in order; first match wins (`continue` while no thread and candidates remain, then `break`) (:626-834).

### Hash-gated prefix grammar (the security core)
```php
// :633 — agent replying to an email notification
preg_match('/^'.$this->formatMessageIdPrefix(\MailHelper::MESSAGE_ID_PREFIX_NOTIFICATION)."-(\d+)-(\d+)-([a-z0-9]+)/", ...)
// :640-656 — thread id accepted ONLY if 16-char hash matches app-key-derived digest
$message_id_hash = $m[3];
if (strlen($message_id_hash) == 16) {
    if ($message_id_hash == \MailHelper::getMessageIdHash($m[1])) { $prev_thread_id = $m[1]; }
}
// MailHelper.php:655-658
public static function getMessageIdHash($thread_id) {
    return substr(md5($thread_id.config('app.key')), 0, 16);
}
```
Invalid/short hash ⇒ log error, setSeen, RETURN — never fall back to trusting the raw thread id ("No backward compatibility for security reasons", GHSA-6r38-6mcf-2ww3). The same gate guards `FS_reply-<thread>-<hash>@` and `FS_autoreply-<thread>-<hash>@` (:686-716).

**Flow continued:** matched notification-prefix ⇒ `$user = User::find($m[2])`, `$message_from_customer = false`; auto-responder headers to notifications are dropped entirely (:669-675). Customer arm resolves prev thread by hash-prefixed ids, else plain `Thread::where('message_id')`. Cross-mailbox guard (:750-805): a customer reply whose prev thread lives in ANOTHER mailbox only threads if that mailbox's own generated-id variant (or the original id recovered from stored raw headers, #5308) exists in THIS mailbox — otherwise `$is_reply = false` and a new conversation starts. Agent-forward detector (:812-824): `^[[:alpha:]]{1,3}\s*:` subject prefix + different mailbox ⇒ new conversation, not a reply.
**Invariant:** a thread-id embedded in a Message-ID is NEVER trusted without its 16-hex-char `md5(id . app.key)` witness; every early-exit path calls `setSeen()` first so the message isn't re-imported forever. Prefix regexes go through `formatMessageIdPrefix()` which makes `FS_` optional for backward compat (`str_replace('FS_', '(?:FS_)?', $prefix)`, :1063-1066).
**Probe:** `grep -c "getMessageIdHash" app/Misc/Mail.php` (= 1 definition site; call sites: `grep -rn "getMessageIdHash(" app/ --include='*.php' | wc -l` = 7 across FetchEmails ×3, SendNotificationToUsers, SendAutoReply job, Thread).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "processMessage message id prev thread", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the candidate-ladder (In-Reply-To → References chain → base64 body marker), the key-hash-witnessed prefix grammar, and the cross-mailbox re-import flip as portable behavior; adapt the md5/app.key digest to your HMAC of choice keeping the 16-char fixed length check; omit Jira-specific rewriting unless you need that integration. Direct tests: none upstream target this ladder (MessageIdAssasinTest pins only spam-filter friendliness of GENERATED ids).
