<!-- capsule-v2 -->
# Timezone-banded daily digest — DB-filtered local-hour recipients with a three-gate send

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you send a "daily at 08:00 local time" digest from one hourly cron run without loading the whole user table or double-sending across timezone bands?

## Hourly command with an indexed timezone band
**Path/Symbol:** `app/Console/Commands/SendTaskDigestCommand.php` (`recipientsAtLocalHour(int $hour): Builder` :51-64, `timezonesAtLocalHour` :68-73, `sendForUser` :76-97); payload source `app/Services/Notifications/DigestService.php` (127L, `forUser(User $user): DigestPayload`).
**Signature:** `handle(DigestService $digestService)` → `recipientsAtLocalHour(8)->with(['ownedTeams','teams'])->chunkById(500, ...)` → per user `sendForUser()` → `Mail::to($user)->send(new TaskDigestMail($user, $payload))` (queued mailable).
**Data Shape:** `timezonesAtLocalHour` filters `DateTimeZone::listIdentifiers()` to zones where `(int) Date::now($tz)->format('G') === $hour`. `DigestPayload` is a readonly DTO tree: `list<DigestTeamSection{teamName, overdue: list<DigestTaskItem>, upcoming: list<DigestTaskItem>}>` with `isEmpty()` (array_all over sections) and `taskCount()`.

### Decisive source
```php
$timezones = $this->timezonesAtLocalHour($hour);
$appTimezoneMatches = in_array((string) config('app.timezone'), $timezones, true);

return User::query()->where(function (Builder $query) use ($timezones, $appTimezoneMatches): void {
    $query->whereIn('timezone', $timezones);

    if ($appTimezoneMatches) {
        $query->orWhereNull('timezone');
    }
});
```
The `orWhereNull` is conditional BY DESIGN: null-timezone users fall back to the app default via `User::effectiveTimezone()` (`timezone ?? config('app.timezone')`), so they belong to the app zone's band only — adding it unconditionally would put them in every band and multiply-send them. The DB filter is coarse (an indexed `whereIn` on ~1/24th of zones); `sendForUser` re-checks the exact hour (`$localNow->hour !== 8`), the per-user preference (`wantsNotification(NotificationType::TaskDigest, NotificationChannel::Email)`), and the payload (`$payload->isEmpty()`), so the queue only ever receives real digests.

**DigestService window (same calendar discipline as MyTasksService):** `startOfToday = Date::now($tz)->startOfDay()->utc()`, `windowEnd = startOfToday->copy()->addDay()`; per team, field metadata resolves in ONE round-trip (`MAX(CASE WHEN cf.code = 'due_date'/'status' THEN ...)` over `custom_fields` ⋈ `custom_field_options` filtered `opt.name = 'Done'`); a missing due field returns an empty section; the task query left-joins `custom_field_values` on the due field, `whereNotNull('due.datetime_value')` + `< windowEnd`, excludes Done via `whereNotExists` on the status `string_value`, orders `due.datetime_value` ASC, and buckets `< startOfToday` → overdue else upcoming. Edit URLs use the Filament modal convention `tableAction=edit&tableActionRecord=<id>` — the same convention ChatContextService reads and MyTasksService writes.

**Flow:** hourly cron → timezone band computed from live clocks → indexed DB filter → chunked per-user triple gate (hour, preference, non-empty payload) → queued markdown mail with per-team sections and manage-preferences link.
**Invariant:** A user is mailed at most once per local day, and only from the band containing their effective timezone; every suppression (empty payload, channel off, hour mismatch) happens before `Mail::` is touched. The window is computed in the recipient's timezone, never the app's.
**Probe:** `tests/Feature/Notifications/SendTaskDigestCommandTest.php` — 08:00-only send; Tokyo queued while UTC user at 23:00 UTC is not; empty-payload and channel-off suppression. `tests/Feature/Notifications/DigestServiceTest.php` — overdue/today-only window, done/undated exclusion, multi-team grouping, Tokyo recipient-timezone window (2026-06-28 23:00 UTC → task due 2026-06-29 10:00 UTC lands in Tokyo's "upcoming").

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "recipientsAtLocalHour timezonesAtLocalHour DigestService forUser whereIn timezone orWhereNull", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the band-then-verify pattern: a coarse indexed DB filter over timezone identifiers plus an exact per-user re-check, and the conditional null-timezone orWhere bound to the app-default fallback. Adopt the one-round-trip EAV metadata probe and the startOfLocalDay→UTC window for any "due today" semantics. Adapt the hour (8), chunk size (500), and the DTO tree to your mail payload. Omit the Filament URL conventions if you have no panel. Companion to `my-tasks-calendar-severity.md` (same window arithmetic) and `chat-page-context-url-binding.md` (same modal URL convention).
