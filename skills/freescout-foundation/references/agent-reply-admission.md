<!-- capsule-v2 -->
# Agent reply-by-email admission — how do you accept support-agent replies sent from their own mail client without letting strangers hijack tickets?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** Once an inbound email resolves to a user (agent) via the notification Message-ID grammar, what identity and authorization gates must pass before the reply is saved?

## saveUserThread admission gates
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:1006-1043` (gates), `:1357-1474` (`saveUserThread`).
**Signature:** `saveUserThread($mailbox, $message_id, $prev_thread, $user, $from, $to, $cc, $bcc, $body, $attachments, $headers, $date)`.
**Data Shape:** thread type=TYPE_MESSAGE, source_via=PERSON_USER, `created_by_user_id`; To forced to conversation's customer_email.

### Decisive source
```php
// app/Console/Commands/FetchEmails.php:1007-1034 — three refusals, each setSeen-first
// 1) Sender address mismatch
if (!$user->hasEmail($from)) {
    $this->logError("Sender address {$from} does not match ".$user->getFullName()." ...");
    $this->setSeen($message, $mailbox);
    \App\Jobs\SendEmailReplyError::dispatch($from, $user, $mailbox)->onQueue('emails');
    return;
}
// 2) Previous thread could not be determined
if (!$prev_thread) { ... return; }
// 3) Agent lost access to the mailbox/conversation
if (!$user->can('view', $prev_thread->conversation)) { ... return; }
```
Alternate-address escape hatch: `$user->hasEmail` covers the profile's Alternate Emails list; the error message TELLS the agent to add that address (#5047 UX). Assignee policy after save (:1372-1387): switch on `$mailbox->ticket_assignee` — ANYONE ⇒ unassign; REPLYING_UNASSIGNED ⇒ claim only if unassigned; REPLYING ⇒ always claim; KEEP_CURRENT ⇒ untouched. Status-after-reply honors `$mailbox->ticket_status` with KEEP_CURRENT passthrough (:1400-1406).
**Invariant:** a rejected agent email still gets marked Seen AND generates a polite "unable to process your update" reply job — silent drops are reserved for auto-responders. The saved thread's TO is rewritten to the CUSTOMER's address (:1433-1434) regardless of what the agent addressed, so downstream threading headers stay canonical.
**Probe:** `grep -c "SendEmailReplyError" app/Console/Commands/FetchEmails.php` (= 1) and `grep -c "TICKET_ASSIGNEE_" app/Console/Commands/FetchEmails.php` (= 4).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "saveUserThread", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt hasEmail → prev-thread-exists → policy-view gate ordering plus the four-way assignee switch as portable behavior; adapt the alternate-email model and ticket_status enum; omit SendEmailReplyError only if you have no equivalent courtesy bounce. Direct tests: none upstream for these gates.
