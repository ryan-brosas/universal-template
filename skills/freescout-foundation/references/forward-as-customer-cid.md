<!-- capsule-v2 -->
# Forward-as-customer & body extraction — how do you recover the real sender from a forwarded email and inline its images?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** When an agent forwards a customer's email into the helpdesk, how is `@fwd` detected, the original sender extracted from arbitrary HTML, and CID-referenced attachments rewritten to stored URLs?

## @fwd substitution ladder
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:25` (`FWD_AS_CUSTOMER_COMMAND = '@fwd'`), `:864-909` (gate), `:1069-1096` (`getOriginalSenderFromFwd`).
**Signature:** `getOriginalSenderFromFwd($body): string` (sanitized email or '').
**Data Shape:** gate requires ALL of: non-empty body; subject matching generic prefix regex `/^[[:alpha:]]{1,3}\s*:(.*)/i` (F:/FW:/FWD:/WG:/De: — 1-3 letters + colon); NOT already a reply/forward-thread match; exactly ONE To recipient and ZERO CC; and the STRIPPED body starting with literal `@fwd`.

### Decisive source
```php
// app/Console/Commands/FetchEmails.php:1072-1095 — sender extraction from hostile HTML
$body = preg_replace("/[\"']cid:/", '!', $body);          // kill cid: false positives
$body = preg_replace("/".self::FWD_AS_CUSTOMER_COMMAND."([\s<]+)/isu", '$1', $body);
$body = preg_replace("/mailto:/i", "", $body);            // #5480
$body = html_entity_decode($body, ENT_QUOTES | ENT_HTML5, "UTF-8");  // &lt;a@b&gt; → <a@b>
$body = preg_replace("/\\\@/", "", $body);                // CSS CJK font names \@DengXian (#5480)
preg_match("/[\"'<:;]([^\"'<:;!@\s]+@[^\"'>:&@\s]+)[\"'>:&]/", $body, $b);
$email = preg_replace("#.*&lt(.*)&gt.*#", "$1", $email);  // residual entity form (#2517)
return Email::sanitizeEmail($email);
```
On match with a verified existing USER as forwarder (`User::nonDeleted()->where(email)` OR alternate-email lookup #5047): `$from = $original_sender`, subject = prefix-stripped group 1, `message_from_customer = true`, `@fwd` removed from body (:899-907) — the conversation is born as if the customer sent it.
**Invariant:** the forwarder must ALREADY be an agent user — anonymous forwarders never trigger substitution (anti-spoofing). The email-extraction charset class excludes `!@` in local part and `&@` in domain so partial entities can't forge separators.

## CID → attachment-URL rewriting
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:1672-1728` (`replaceCidsWithAttachmentUrls`) called from both save paths (:1294,:1449).
**Data Shape:** input = saved-attachment pairs `[imap_attachment, attachment]`; embedded flag persisted per Attachment when its cid matched.
```php
// :1703-1715
if ($attachment['imap_attachment']->id && (... img_src || strlen(content))) {
    $cid = 'cid:'.$attachment['imap_attachment']->id;
    if (strstr($body, $cid)) {
        $body = str_replace($cid, $attachment['attachment']->url(), $body);
        $attachment['attachment']->embedded = true; $attachment['attachment']->save();
    } else { $only_embedded_attachments = false; }
}
// :1718-1725 — if EVERY attachment was embedded and conversation had none before, undo has_attachments
if ($only_embedded_attachments && $conversation->has_attachments && !$prev_has_attachments) {
    $conversation->has_attachments = false; $conversation->save();
}
```
**Invariant:** an attachment counts toward `has_attachments` only if it is NOT embedded AND survived URL replacement — signature images must not flip paperclip icons. Base64 data-URI images get a second pass (`Thread::replaceBase64ImagesWithAttachments`, FetchEmails.php:1305-1313) converting inline base64 blobs into stored attachments.
**Probe:** `grep -c "FWD_AS_CUSTOMER_COMMAND" app/Console/Commands/FetchEmails.php` (= 4) and `grep -c "replaceCidsWithAttachmentUrls" app/Console/Commands/FetchEmails.php` (= 3).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "getOriginalSenderFromFwd cid", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the multi-gate forward detection, hostile-HTML sender extraction sequence (order matters), and embedded-vs-real attachment accounting; adapt the `@fwd` token and user-verification store to yours; omit base64 conversion if your sanitizer already detaches inline images. Direct tests: none upstream for either seam.
