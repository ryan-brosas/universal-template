<!-- capsule-v2 -->
# Auto-reply loop guard — how do you auto-respond to customers without feeding autoresponder wars?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** What gates decide an auto-reply is safe to send, and how does the system provably terminate vacation-responder ping-pong?

## SendAutoReply listener ladder
**Path/Symbol:** `app/Listeners/SendAutoReply.php:24` (`handle`, 24–105).
**Signature:** `public function handle($event)` on `CustomerCreatedConversation` (EventServiceProvider.php:91-94).
**Data Shape:** `CHECK_PERIOD = 180` minutes; thresholds: ≥10 recent auto-replies to a customer = hard stop, ≥2 = subject-collision check; SendLog rows filtered by `mail_type = MAIL_TYPE_AUTO_REPLY`.

### Decisive source
```php
// app/Listeners/SendAutoReply.php:56-77 — bounded-rate + duplicate-subject guards
$auto_replies_sent = SendLog::where('customer_id', $conversation->customer_id)
    ->where('mail_type', SendLog::MAIL_TYPE_AUTO_REPLY)
    ->where('created_at', '>', $created_at)     // now - 180 min
    ->count();
if ($auto_replies_sent >= 10) { return; }
if ($auto_replies_sent >= 2) {
    foreach ($prev_conversations as $prev_conv) {
        if ($prev_conv->subject == $conversation->subject && $prev_conv->id != $conversation->id) { return; }
    }
}
// :79-85 — never answer your own mailboxes
if ($conversation->customer_email) {
    $is_internal_email = Mailbox::where('email', $conversation->customer_email)->exists();
    if ($is_internal_email) { return; }
}
```

**Flow — full gate order:** skip imported conversations and disabled mailbox auto_reply (:30-34) → drop auto-RESPONDERS (`$thread->isAutoResponder()` wraps `MailHelper::isAutoResponder`, Mail.php:667-706: x-autoreply/x-autorespond/x-autoresponder any-value; auto-submitted any-value; delivered-to=autoresponder; precedence/x-precedence ∈ {auto_reply,bulk,junk,list}) → drop bounces (`$thread->isBounce()`) → drop spam conversations → Eventy veto → rate ladder above → internal-mailbox check → dispatch job `onQueue('emails')`. The JOB re-checks `meta['ar_off']` at send time and answers with `In-Reply-To`+`References` pointing at the customer thread and a hash-gated `FS_autoreply-<thread>-<hash>@` Message-ID.
**Invariant:** the comment at :47-51 states the core risk: bounce detection is not 100 % reliable, so the ONLY guaranteed termination for the auto-reply↔bounce loop is the counting guard — a porter must keep BOTH the header-based autoresponder filter (fast path) AND the SendLog count ceiling (soundness backstop). The subject-collision check at ≥2 catches two of the user's own conversations echoing each other. Auto-replies to email NOTIFICATIONS are additionally dropped in the fetcher itself (FetchEmails.php:669-675) before any thread is created.
**Probe:** `grep -c "MAIL_TYPE_AUTO_REPLY" app/Listeners/SendAutoReply.php` (= 2; the job adds a third site: `grep -rc "MAIL_TYPE_AUTO_REPLY" app/Jobs/SendAutoReply.php` = 1) and `grep -c "isAutoResponder" app/Listeners/SendAutoReply.php` (= 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "SendAutoReply", limit: 5, fields: ["signature","name","file"] });
```
(two same-named classes exist — Listener vs Job; route by path.)

## Verdict
Adopt gate ordering (responder headers → bounce → spam → rate ceiling → self-mailbox), the 10-cap/2-suspect SendLog accounting, and delayed-dispatch via the reply queue; adapt precedence-header lists to your parser; omit the phone/chat branches if you have no non-email channels. Direct tests: none upstream.
