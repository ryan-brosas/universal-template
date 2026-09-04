<!-- capsule-v2 -->
# Reply-separation shortest-wins ladder — how do you cut a quoted thread out of an email body?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How is the customer's new reply extracted from a reply/forward body when every mail client quotes the old text differently — and which separator wins?

## FetchEmails::separateReply
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:1530` (`separateReply`, 1530–1670).
**Signature:** `public function separateReply($body, $is_html, $is_reply, $user_reply_to_notification = false, $prev_message_id = '')`.
**Data Shape:** input = raw HTML (or text) body; output = HTML fragment of just the new message; separator sources = `Mail::$alternative_reply_separators` + per-mailbox `$mailbox->before_reply` + optional hashed marker.

### Decisive source
```php
// app/Console/Commands/FetchEmails.php:1636-1666 — try every separator, keep SHORTEST result
foreach ($reply_separators as $reply_separator) {
    if (\Str::startsWith($reply_separator, 'regex:')) {
        $regex = preg_replace("/^regex:/", '', $reply_separator);
        $parts = preg_split($regex, $result);
    } else {
        $parts = explode($reply_separator, $result);
    }
    if (count($parts) > 1) {
        if ($user_reply_to_notification) {           // Outlook puts its header block ABOVE the quote
            $parts[0] = preg_replace('/<hr[^>]*>\s*<div[^>]+id="(?:x_)?divRplyFwdMsg".*$/is', '', $parts[0]) ?: $parts[0];
        }
        $text = \Helper::htmlToText($parts[0]);      // candidate must contain real text
        ...
        if ($text) { $reply_bodies[] = $parts[0]; }
    }
}
if (count($reply_bodies)) {
    usort($reply_bodies, $cmp_reply_length_desc);    // mb_strlen ASC
    return $reply_bodies[0];
}
```
`$cmp_reply_length_desc` (:1532-1538) sorts by `mb_strlen` ascending despite its name — shortest candidate = least over-quoted.

**Flow:** preprocess via Eventy hook (`fetch_emails.separate_reply.preprocess_body`) → HTML arm: Proton quirk first (`<div class="protonmail_quote">` before `<html>` ⇒ truncate there, #4537), then collect ALL `<html>…</html>` blocks and keep each `<body>` inner HTML; Yahoo-Android pre-`<html>` plain fragments are PREPENDED so they can be separated (#5409); fallback to whole body → `$is_reply` ladder above. Text arm: `nl2br()` only.
**Invariant:** a candidate split is valid ONLY if the part above the separator still contains real text after `htmlToText`+trim+leading-whitespace strip (`preg_replace('/^\s+/mu', ...)`). When the agent replies to a NOTIFICATION and the special marker `\MailHelper::REPLY_SEPARATOR_NOTIFICATION` (`fsNotifReplyAbove`, Mail.php:18) is present, ALL other separators are discarded (:1617-1621). When `config('app.alternative_reply_separation')` is on and a hashed separator `fsReplyAbove + substr(md5(message_id.app.key),0,8)` (`MailHelper::getHashedReplySeparator`, Mail.php:1341-1350) exists in the body, it alone is used (:1627-1634).
**Probe:** `grep -c "divRplyFwdMsg" app/Console/Commands/FetchEmails.php` (= 2 — one in code :1650, one in comment :1646) and `grep -c "divRplyFwdMsg" tests/Unit/ReplySeparationTest.php` (= 3 across two fixture bodies).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "separateReply", limit: 5, fields: ["signature","name","file"] });
```
(resolves line-exact: `FetchEmails.separateReply app/Console/Commands/FetchEmails.php 1530-1670`.)

## Direct tests (gate 3 evidence)
`tests/Unit/ReplySeparationTest.php` instantiates the real command object and asserts two fixtures end-to-end: German Outlook mobile body (`Von:/Gesendet:` header div) → `<p>Hi\n</p>`, both for customer replies AND for `$user_reply_to_notification = true` with the rewritten-id notification table (`x_fsNotifReplyAbove` class but intact `data-fs` attribute).

## Verdict
Adopt shortest-candidate-wins + text-presence validation + single-separator override ladders; adapt client-specific quirks (Proton/Yahoo/Outlook) as data-driven separator entries incl. your own `regex:` prefix convention; omit the DOMDocument/LIBXML_PARSEHUGE specifics if your sanitizer differs — but keep the "extract every <body>, then split" ordering. Direct test: upstream ReplySeparationTest pins the Outlook-notification case.
