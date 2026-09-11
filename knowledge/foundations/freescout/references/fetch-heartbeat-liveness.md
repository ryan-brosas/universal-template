<!-- capsule-v2 -->
# Fetch heartbeat & liveness options — how do you detect a silently-dead cron pipeline and alert exactly once?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How do the fetch command's timestamp writes and the monitor's edge-triggered latch cooperate to send one alert on failure and one recovery notice — never spam?

## Two timestamps + one latch
**Path/Symbol:** `app/Console/Commands/FetchEmails.php:81-84,183-185` (writers), `app/Console/Commands/FetchMonitor.php:38-72` (reader).
**Signature:** `Option::set('fetch_emails_last_run'| 'fetch_emails_last_successful_run', time())`; monitor reads both + `alert_fetch_period` via `Option::getOptions([...])`.
**Data Shape:** `$now = time()` captured ONCE at handle() start; success stamp written only when `$successfully && count($mailboxes)`; `alert_fetch_sent` Option acts as boolean latch.

### Decisive source
```php
// app/Console/Commands/FetchMonitor.php:48-68
if ($last_successful_run && $last_successful_run < $now - ((config('app.fetch_schedule') * 60) + ($options['alert_fetch_period'] * 60))) {
    $mins_ago = floor(($now - $last_successful_run) / 60);
    ...
    if (\Option::get('alert_fetch') && !\Option::get('alert_fetch_sent')) {
        \Option::set('alert_fetch_sent', true);        // LATCH before sending
        \MailHelper::sendAlertMail($text, 'Fetching Problems');
    }
} elseif (!$last_successful_run) { ... } else {
    if (\Option::get('alert_fetch_sent')) {
        \MailHelper::sendAlertMail('...Fetching recovered and functioning now!', 'Fetching Recovered');
    }
    \Option::set('alert_fetch_sent', false);           // unlatch every healthy tick
}
```
**Flow:** fetch run stamps `fetch_emails_last_run` unconditionally (even on failure) so the UI can show "cron ran but errored"; the SUCCESS stamp gates on zero mailbox errors AND at least one mailbox existing (:183-185). Threshold adds the configured cadence (`fetch_schedule` minutes ×60) to the alert period, so a legitimately-slow hourly schedule doesn't trip a 15-min alert.
**Invariant:** alert fires ONLY while `alert_fetch` (user opt-in) is set AND the latch is clear — the latch is set BEFORE the send attempt, so a failing mailer can't cause infinite retry-spam of the alert itself. Recovery mail requires a previously-latched failure; a healthy first-ever run just unlatches silently. Distinct error class: duplicate-entry POP3 races are explicitly non-alerting inside the fetch loop (FetchEmails.php:157-163).
**Probe:** `grep -c "fetch_emails_last" app/Console/Commands/FetchEmails.php` (= 2) and `grep -c "alert_fetch_sent" app/Console/Commands/FetchMonitor.php` (= 3).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "FetchMonitor last successful run", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt dual-timestamp heartbeat + cadence-aware threshold + set-before-send latch + explicit unlatch as the portable liveness pattern; adapt Option storage and mail transport; omit the recovered-email branch only if you have no users to reassure. Direct tests: none upstream.
