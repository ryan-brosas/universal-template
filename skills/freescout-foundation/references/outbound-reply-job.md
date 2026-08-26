<!-- capsule-v2 -->
# Outbound reply job — retry ladder, References trimming, and send-status state machine

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How does a queued reply-to-customer email retry on SMTP failure without double-sending, and how are threading headers built for long conversations?

## SendReplyToCustomer::handle
**Path/Symbol:** `app/Jobs/SendReplyToCustomer.php:67` (`handle`, 67–584).
**Signature:** `public function handle()` on a queued job constructed with `($conversation, $threads, $customer)`; `$tries = 168` (one per hour for a week), `$timeout = 120`s (Swift fwrite can hang forever, :41-47).
**Data Shape:** `$this->threads` = collection sorted NEWEST-first (`Thread::sortThreads`, desc by created_at then id, Thread.php:1569-1584); headers array → Swift message.

### Decisive source
```php
// app/Jobs/SendReplyToCustomer.php:395-418 — failure taxonomy and release ladder
preg_match('#but got code "(\d+)",#', $error_message, $response_m);
$response_code = (int)($response_m[1] ?? 0);
if ($this->attempts() < $this->tries && !preg_match("/".config("app.no_retry_mail_errors")."/i", $error_message)) {
    if ($this->attempts() == 1) { $this->release(300); }   // second attempt after 5 min
    else                        { $this->release(3600); }  // others after 1 hour
    if ($this->attempts() >= 3 || $response_code >= 500) {
        $this->last_thread->send_status = SendLog::STATUS_SEND_INTERMEDIATE_ERROR;
        $this->last_thread->updateSendStatusData(['msg' => $error_message]);
        ...
    }
    throw $e;                                              // rethrow so the queue counts the attempt
} else { ... STATUS_SEND_ERROR ... $this->fail($e); }
```
Idempotence gate (:145-150): on ANY retry (`attempts() >= 1`) the job returns immediately if the last thread's send_status is already ACCEPTED or any success status — the IMAP-sent-folder append or memory blowup (#3632) that killed attempt 1 cannot cause a resend after a recorded success.
**Flow:** guard deleted conversation/mailbox → merge forwarded-parent replies when the child conversation has exactly one forwarded thread (trimming threads created AFTER the forward parent, :84-121) → build `In-Reply-To` from the newest CUSTOMER thread (:166-171) → **References trimming** (:184-215): budget `$max_references_length = 1500` chars, always keep FIRST + LAST reference, drop middle ones until under budget, then `array_reverse` so oldest-first per RFC 5322 §3.6.4 → Outlook `Thread-Index`/`Thread-Topic` passthrough from the customer thread (:221-232) → history policy (`email_conv_history` full/last/none/global; forwards force 'full', :235-263) → `MailHelper::setMailDriver($mailbox,...)` per-send config swap → register SwiftGetSmtpQueueId plugin once per process (:277-281) → recipient sanitation (strip mailbox's own addresses, remove customer from CC/BCC, auto_bcc append, CC wins over BCC dedupe, :310-329) → send.

### Decisive source (success path + queue-id capture)
```php
// :359-368 + Mail/SwiftGetSmtpQueueId.php:9-19
$this->last_thread->send_status = SendLog::STATUS_ACCEPTED;
$this->last_thread->save();
$smtp_queue_id = SwiftGetSmtpQueueId::$last_smtp_queue_id;   // captured from SMTP 'queued as <id>' response
```
A registered Swift ResponseListener parses `queued as X` into a static — the ONLY way to persist the upstream queue id, since Laravel discards SMTP chatter. After success: clear stale SEND_ERROR (`send_status = null`, msg ''), optional IMAP sent-folder append of the RAW MIME string (`\MailHelper::$smtp_mime_message` captured inside the Mailable's withSwiftMessage callback, ReplyToCustomer.php:144-146) with every failure mode log-and-continue, then `saveToSendLog()` writes one SendLog row PER RECIPIENT (STATUS_ACCEPTED vs STATUS_SEND_ERROR by membership in `Mail::failures()`).
**Invariant:** send_status is a monotone-ish ledger — INTERMEDIATE_ERROR at ≥3 attempts or 5xx, terminal SEND_ERROR only via `$this->fail()`, cleared on late success; recipients, not threads, carry per-address outcomes in SendLog. `failed(Exception)` logs to activity + saveToSendLog using constructor-only state (Laravel serializes job props between attempts).
**Probe:** `grep -c "release(" app/Jobs/SendReplyToCustomer.php` (= 2) and `grep -c "max_references_length" app/Jobs/SendReplyToCustomer.php` (= 2 — definition :189 + budget check :200).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "SendReplyToCustomer", limit: 5, fields: ["signature","name","file"] });
```
(rank#1 = `app/Jobs/SendReplyToCustomer.php 67-584`; note the twin listener class of the same name in `app/Listeners/` — route by file path.)

## Verdict
Adopt attempts-based backoff ladder, accepted-status idempotence gate, first+last References preservation under a byte budget, and per-recipient SendLog semantics; adapt Swift/Laravel queue plumbing to your stack keeping the "capture SMTP queue id via transport event" trick; omit IMAP sent-folder mirroring unless you have raw-MIME access. Direct tests: none upstream for this job.
