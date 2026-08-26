<!-- capsule-v2 -->
# Bounce detection ladder — how do you recognize a delivery-status notification and find the original message it bounces?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** What independent signals mark an inbound email as a bounce, and how is the bounced thread recovered from the DSN?

## Four-signal OR ladder in processMessage
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:502-605`.
**Signature:** inline ladder; outputs `$is_bounce: bool` + `$bounced_message_id: ?string`.
**Data Shape:** signals read attachments (Webklex Attachment objects), raw header block string, and From address; `$bounced_message_id` is extracted from the FIRST attached `message/rfc822`-ish part's embedded headers.

### Decisive source
```php
// app/Console/Commands/FetchEmails.php:546-566 — signal 1: attachment content-type
if (!empty(Attachment::$types[$attachment->getType()]) && ... == Attachment::TYPE_MESSAGE) {
    if (preg_match('/delivery-status/', strtolower($attachment->content_type))) {
        $is_bounce = true;
        if (!$bounced_message_id) {
            $bounced_message_id = \MailHelper::getHeader($attachment->getContent(), 'message_id');
        }
    }
}
// :573-577 — signal 2: Content-Type multipart/report + report-type=delivery-status
if (!$is_bounce && $message_header) { $is_bounce = \MailHelper::detectBounceByHeaders($message_header); }
// MailHelper.php:716-726 — two regexes must BOTH match on the folded header value
preg_match("/Content-Type:((?:[^\n]|\n[\t ])+)(?:\n[^\t ]|$)/i", ...)
  && preg_match("/multipart\/report/i", ...) && preg_match("/report-type=[\"']?delivery-status[\"']?/i", ...)
// :579-593 — signal 3: /^mailer-daemon@/i From; signal 4: /^Return-Path: <>/i header line
```

**Flow:** any signal sets `$is_bounce`; if no `$bounced_message_id` yet, scan remaining attachments for literal `content_type == 'message/rfc822'` and pull its inner `Message-ID` header (:595-605). After a successful customer-thread save, `saveBounceData($new_thread, $bounced_message_id, $from)` runs (:1049-1052).
**Invariant:** each check runs only `if (!$is_bounce)` — first hit wins and later checks never overwrite. The DSN's embedded Message-ID is resolved through the SAME hash-gated prefix grammar as replies (`saveBounceData` matches `FS_reply|FS_autoreply-(\d+)-` and trusts `\d+` only after prefix match, FetchEmails.php:1098-1119). Auto-replies to bounces are separately suppressed by the SendAutoReply loop-guard capsule.
**Probe:** `grep -c "delivery-status" app/Console/Commands/FetchEmails.php` (= 1, :553) and `grep -c "detectBounceByHeaders" app/Misc/Mail.php` (= 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "bounce delivery status detect", limit: 10, fields: ["signature","name","file"] });
```

## saveBounceData — cross-conversation status write-back
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:1098-1142`.
```php
$bounced_thread->send_status = SendLog::STATUS_DELIVERY_ERROR;
$status_data = ['bounced_by_thread' => $new_thread->id, 'bounced_by_conversation' => $new_thread->conversation_id];
$bounced_thread->updateSendStatusData($status_data);
...
SendLog::log($bounced_thread->id, null, $from, SendLog::MAIL_TYPE_EMAIL_TO_CUSTOMER,
             SendLog::STATUS_DELIVERY_ERROR, $bounced_thread->created_by_customer_id, null, 'Message bounced');
```
The bounce notice itself becomes a customer-visible thread whose send_status_data carries `is_bounce/bounce_for_thread`, while the ORIGINAL outbound thread flips to STATUS_DELIVERY_ERROR plus `bounced_by_*` pointers — bidirectional linkage without a schema join. Soft vs hard bounces both map to DELIVERY_ERROR (comment :1139).

## Verdict
Adopt the four-signal OR ladder with first-hit-wins ordering and embedded-message-id extraction; adapt the SendLog status vocabulary to your own; omit the exact regex set only if you have a full DSN parser — otherwise keep both multipart/report conditions ANDed. Direct tests: none upstream for this ladder.
