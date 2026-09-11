<!-- capsule-v2 -->
# Mail-var templating — how do you merge `{%mailbox.name%}`-style variables with fallbacks into notification emails?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** What is the variable grammar, fallback syntax, escaping contract, and recursion guard when rendering user-editable email templates?

## MailHelper::replaceMailVars
**Path/Symbol:** `app/Misc/Mail.php:287-372` (`replaceMailVars`), `:377-380` (`hasVars`).
**Signature:** `replaceMailVars($text, $data = [], $escape = false, $remove_non_replaced = false): string`.
**Data Shape:** grammar `{%<dotted.var>(,fallback=<literal>)?%}`; var universe built from `$data` keys conversation/mailbox/customer/user (subject, number, customer_email, mailbox email/name/fromName, customer fullName/firstName/lastName/company, user fullName/firstName/phone/email/jobTitle/photoUrl); Eventy filters `mail_vars.replace` and `mail_vars.replace_after_fallback` extend it.

### Decisive source
```php
// app/Misc/Mail.php:330-363 — two-phase merge keeps both bare and full-match keys
preg_match_all('#\{%(?<var>[a-zA-Z.]+)(,fallback=(?<fallback>[^}]*))?%\}#', $text, $matches);
foreach ($matches['var'] as $i => $var) {
    $merge_code   = "{%{$var}%}";
    $full_match   = $matches[0][$i];
    $has_fallback = false !== strpos($full_match, ',fallback=');
    $fallback_val = $has_fallback ? $matches['fallback'][$i] ?? null : null;
    $merge_val    = isset($vars[$merge_code]) ? $vars[$merge_code] : $fallback_val;
    if (null !== $merge_val || true === $remove_non_replaced) {
        $vars[$full_match] = $merge_val;     // full token incl. fallback → its resolved value
        $vars[$merge_code] = $merge_val;     // bare token → same value
    }
}
if ($escape) { foreach ($vars as $i => $var) { $vars[$i] = htmlspecialchars($var ?? ''); $vars[$i] = nl2br($vars[$i]); } }
else         { foreach ($vars as $i => $var) { $vars[$i] = nl2br($var ?? ''); } }
$result = strtr($text, $vars);
```
Recursion guard (:300-305): `{%mailbox.fromName%}` normally derives from `$mailbox->getMailFrom(...)`, but when the caller passes `mailbox_from_name` explicitly the derived branch is skipped "To avoid recursion" — a mailbox-name template containing itself would otherwise loop.
**Flow:** build base vars from `$data` → filter hook #1 → regex-scan text for tokens WITH fallbacks → resolve each to value-or-fallback → optional strip of still-unresolved tokens via cleanup regex `#\{%[^\.%\}]+\.[^%\}]+\%\}#` + trim → filter hook #2 → escape/nl2br per flag → single `strtr`.
**Invariant:** a variable that is PRESENT but empty string stays empty-string (isset, not empty); fallback fires only on MISSING vars; nl2br applies in BOTH modes so plain-text newlines survive HTML mail — escape adds htmlspecialchars BEFORE nl2br. `hasVars()` cheap-gates callers with a bare `{%|%}` regex.
**Probe:** `grep -c "fallback" app/Misc/Mail.php` (= 7) and `grep -c "strtr" app/Misc/Mail.php` (= 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "replaceMailVars", limit: 5, fields: ["signature","name","file"] });
```

## Direct tests (gate 3 evidence)
`tests/Unit/MailVarsTest.php` exercises replaceMailVars end-to-end against fixture templates (fallback resolution and removal modes).

## Verdict
Adopt the dotted-token grammar, explicit-fallback clause, dual-key strtr merge, and escape-before-nl2br ordering; adapt the var universe to your domain; omit the recursion guard ONLY if your templates can't self-reference. Direct test: upstream MailVarsTest.
