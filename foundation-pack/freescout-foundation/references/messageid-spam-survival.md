<!-- capsule-v2 -->
# Message-ID spam-filter survival — how do you generate outbound Message-IDs that threading needs but spam filters won't flag?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** What grammar must generated Message-IDs and body markers follow so replies thread AND pass SpamAssassin?

## Prefix + hash grammar
**Path/Symbol:** `app/Misc/Mail.php:25-30` (prefixes), `:655-658` (`getMessageIdHash`), `:882-895` (`generateMessageId`/`isGeneratedMessageId`), `:1399-1402` (`isFsMessageId`), `Thread.php:1548-1561` (`getMessageId`).
**Signature:** `getMessageIdHash($thread_id): string` = `substr(md5($thread_id.config('app.key')), 0, 16)`; `generateMessageId($email_address, $raw_body = '')` = `'fs-'.($raw_body ? md5(strval($raw_body)) : str_random(16)).'@'.preg_replace("/.*@/", '', $email_address)`.
**Data Shape:** four prefixes: `FS_notify-<thread>-<user>-<hash>`, `FS_conversation-<conv>-<md5>` (notification In-Reply-To anchor), `FS_reply-<thread>-<hash>`, `FS_autoreply-<thread>-<hash>`; `$all_message_id_prefixes` feeds a case-insensitive OR-match for "did we send this?".

### Decisive source
```php
// app/Thread.php:1548-1561 — outbound id minted per send, never stored for user threads
public function getMessageId($mailbox = null) {
    if ($this->isCustomerMessage() && $this->message_id) { return $this->message_id; }
    if ($this->isUserMessage()) {
        if (!$mailbox) { $mailbox = $this->conversation->mailbox; }
        return \MailHelper::MESSAGE_ID_PREFIX_REPLY_TO_CUSTOMER.'-'.$this->id.'-'
             . \MailHelper::getMessageIdHash($this->id).'@'.$mailbox->getEmailDomain();
    }
    return '';
}
```
Body marker twin (`MailHelper::getMessageMarker`, Mail.php:631-653): `'{#FS:'.base64_encode($message_id).'#}'` — comment: **"It has to be BASE64, as Gmail converts it into link"**; parsed back by regex `/{#FS:([^#]+)#}/`. Hashed reply separator (`getHashedReplySeparator`, :1341-1350) appends `substr(md5(message_id.app.key),0,8)` to the visible separator so the fetcher can split replies with zero false positives.
**Flow:** SendReplyToCustomer sets `headers['Message-ID'] = last_thread->getMessageId($mailbox)`; SendNotificationToUsers builds `FS_notify-<thread>-<user>-<hash>@domain` (:126); notification In-Reply-To uses the deterministic fake anchor `FS_conversation-<conv>-<md5(conv)>@domain` (:92-93) so agent replies via mail thread back into the conversation without an existing outbound message.
**Invariant:** ids MUST NOT match SpamAssassin MSGID rules (#5245) — hence 16-hex hash suffixes and lowercase prefixes rather than all-caps or digit-soup; the upstream test pins this adversarially. The hash is keyed on `app.key`: rotating the app key invalidates every future reply-threading match for old notifications (accepted cost; documented in fetcher as "No backward compatibility for security reasons").
**Probe:** `grep -c "MESSAGE_ID_PREFIX" app/Misc/Mail.php` (= 8 — 4 consts + 4 `$all_message_id_prefixes` array members) and `grep -c "getMessageIdHash" tests/Unit/MessageIdAssasinTest.php` (= 0 — test calls getMessageId only; use `grep -c "assasin_regexes" tests/Unit/MessageIdAssasinTest.php` = 2).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "getMessageId message id prefix", limit: 10, fields: ["signature","name","file"] });
```

## Direct tests (gate 3 evidence)
`tests/Unit/MessageIdAssasinTest.php` embeds ~17 SpamAssassin MSGID regexes verbatim and asserts BOTH generated user-reply and customer-thread Message-IDs match NONE of them.

## Verdict
Adopt prefix-id-hash grammar, base64 body marker, hashed separator, and deterministic notification anchor; adapt md5(app.key) to HMAC; omit SpamAssassin regex set unless you control inbound filtering too. Direct test: upstream MessageIdAssasinTest.
