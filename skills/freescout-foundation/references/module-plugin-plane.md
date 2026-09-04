<!-- capsule-v2 -->
# Module plugin plane — how do you ship extensions that hook filters/actions and survive core upgrades?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How are modules structured, discovered, activated, and licensed — and what does the Eventy filter/action API they program against actually guarantee?

## nwidart/Laravel-Modules layout + WpApi licensing
**Path/Symbol:** module root `Modules/<Name>/` (excluded from graph indexing by design — `index_status.not_indexed.dirs` lists it); registry `app/Module.php:13`; license client `app/Misc/WpApi.php:5+`; scheduler hook `app/Console/Commands/ModuleCheckLicenses.php:39-60`.
**Signature:** `WpApi::httpRequest($method, $url, $params)`; actions `check_license(s)/activate/deactivate/get_version` against ENDPOINT `freescout/v1/modules` on configurable `app.freescout_api` (+ `_alt_api` fallback).
**Data Shape:** module = composer-less Laravel sub-app (routes, views, providers, migrations under one folder); `\Module::getActive()` enumerates enabled ones.

### Decisive source
```php
// app/Console/Kernel.php:60-65 — license check cron jittered by app.key crc32
$app_key = config('app.key');
if ($app_key) {
    $crc = crc32($app_key);
    $schedule->command('freescout:module-check-licenses')
        ->cron((int)($crc % 59).' '.(int)($crc % 23).' * * *');   // deterministic per-install spread
}
// app/Jobs/TriggerAction.php:44-48 — delayed Eventy action execution primitive
public function handle() {
    $args = $this->params;
    array_unshift($args, $this->action);
    call_user_func_array("\Eventy::action", $args);
}
```
Eventy surface the codebase relies on (counted at pin): 100+ `Eventy::filter` points mutating data in-flight (`fetch_emails.unseen`, `fetch_emails.mailbox_to_save_message`, `fetch_emails.data_to_save`, `conversation.status_changing`, `folder.update_counters`, `mail_vars.replace`, `email.reply_to_customer.subject`…) and ~40 `Eventy::action` notification points (`conversation.created_by_customer`, `thread.created`, `mail.reapply_mail_config`…). Filters MUST return their first argument's replacement; actions are fire-and-forget.
**Flow:** helper `Helper::backgroundAction($action, $params, $delay)` (Helper.php:1298-1310) wraps TriggerAction dispatch on the default queue — modules can defer any action. Module lifecycle helpers live as artisan commands (`ModuleInstall/Update/Build/ModuleLaroute`) regenerating routes/assets per module.
**Invariant:** every core extension point is a NAMED STRING filter/action — a porter must keep names stable because modules are external code compiled against them. The crc32-jittered cron prevents thundering herd on freescout.net across thousands of installs while staying deterministic (same install ⇒ same minute).
**Probe:** `grep -c "Eventy::filter" app/Console/Commands/FetchEmails.php` (= 10) and `grep -c "Eventy" app/Misc/Mail.php` (= 4).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "Module licenses wp api", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt string-keyed filter/action plugin API + background-action deferral + deterministic license-cron jitter as portable patterns; adapt Eventy to your container events keeping return-value semantics for filters; omit the WordPress-style marketplace specifics (WpApi endpoints) unless you run a module store. Direct tests: none upstream; Modules/ tree intentionally outside graph coverage — cite source directly when porting a specific module.
