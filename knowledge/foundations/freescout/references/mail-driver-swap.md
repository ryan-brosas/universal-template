<!-- capsule-v2 -->
# Per-mailbox mail-driver swap — how do you send through different SMTP accounts from one long-lived worker?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How does a single queue worker safely reconfigure the global mailer between sends to different mailboxes (and OAuth refresh) without leaking one mailbox's credentials into another's email?

## MailHelper::setMailDriver + reapplyMailConfig
**Path/Symbol:** `app/Misc/Mail.php:160` (`setMailDriver`, 160–224) and `:229` (`reapplyMailConfig`, 229–252).
**Signature:** `setMailDriver($mailbox = null, $user_from = null, $conversation = null)`; `reapplyMailConfig(): bool`.
**Data Shape:** mutates Laravel global `\Config::set('mail.*')`; static `$last_mail_config_hash` guards rebuild; OAuth tokens live in mailbox meta (`oauthGetParam('a_token'/'r_token'/'issued_on'/'expires_in')`).

### Decisive source
```php
// app/Misc/Mail.php:240-249 — the whole trick
$mail_config_hash = md5(json_encode(\Config::get('mail')));
if (self::$last_mail_config_hash != $mail_config_hash) {
    self::$last_mail_config_hash = $mail_config_hash;
} else {
    return false;
}
// Without doing this, Swift mailer uses old config values if there were emails sent with previous config.
\App::forgetInstance('mailer');
\App::forgetInstance('swift.mailer');
\App::forgetInstance('swift.transport');
(new \Illuminate\Mail\MailServiceProvider(app()))->register();
// We have to update Mailer facade manually, as it does not happen automatically:
\Mail::swap(app('mailer'));
```

**Flow:** OAuth branch refreshes an expired access token FIRST (issued_on + expires_in < time ⇒ POST refresh_token grant; Google Workspace quirk — response omits r_token, so carry the old one forward, :176-181; failure logs and CONTINUES for sending, throws only on the fetching side :858-868) → set driver/from/SMTP host/port/auth per mailbox, `XOAUTH2` auth_mode + access-token-as-password when OAuth (:198-216) → hash-compare → container-forget + provider re-register + facade swap. System notifications use `setSystemMailDriver()` (:259-282) reading Option-table SMTP settings with `\Helper::decrypt(password)`.

**Companion listeners:** `RestartSwiftMailer` (on Illuminate MessageSent) forgets the same three instances after EVERY sent message so Swift temp files don't accumulate (#2949); `ProcessSwiftMessage` exposes a `mail.process_swift_message` filter pre-send. Fetch-side twin: `getMailboxClient($mailbox)` (:790-877) writes `imap.accounts.default` config then builds `Webklex\ClientManager(config('imap'))->account('default')`, refreshing the OAuth token before connect.
**Invariant:** config identity is decided by CONTENT HASH, not by call order — two consecutive sends with identical config skip the expensive rebuild; any new config key you add must be inside `Config::get('mail')` or the guard goes stale. The swap is process-global: safe only under single-worker-per-mailbox serialization (FreeScout runs ONE `queue:work --queue=emails` guarded by schedule mutexes).
**Probe:** `grep -c "forgetInstance" app/Misc/Mail.php app/Listeners/RestartSwiftMailer.php | awk -F: '{s+=$2} END {print s}'` (= 6 — three per file).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "setMailDriver reapply config", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt hash-guarded config rebuild + service-container forget trio + facade reswap + post-send restart as THE pattern for multi-account sending in one worker; adapt Config/Swift specifics to your framework (the invariant is content-hash dedupe and full transport reconstruction); omit XOAUTH2 details unless targeting M365/Gmail. Direct tests: none upstream.
