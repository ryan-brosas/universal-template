<!-- capsule-v2 -->
# Deferred assignee fan-out — diff-based recipients, defer() side effects, per-channel preference gates

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you notify only newly assigned users about a task without making notification failure part of the save request, and without re-notifying on every edit?

## Diff-gated, response-deferred notification
**Path/Symbol:** `app/Actions/Task/NotifyTaskAssignees.php` (whole, 76L, `execute(Task $task, array $previousAssigneeIds = []): void`); callers `app/Actions/Task/{CreateTask,UpdateTask}.php` (constructor-injected), `app/Filament/Resources/TaskResource/Pages/ManageTasks.php` :53, `app/Filament/Pages/Dashboard.php` :147; preference source `app/Data/NotificationPreferences.php` (26L) + `app/Enums/Notifications/NotificationType.php` (`defaultEnabled()`).
**Signature:** `array_diff($task->assignees()->pluck('users.id')->all(), $previousAssigneeIds)` → early return when empty → snapshot title/id/url → `defer(function () ...)` → per recipient two independent `wantsNotification(NotificationType::TaskAssigned, NotificationChannel::InApp|Email)` gates → `Notification::...->sendToDatabase($recipient)` and/or `Mail::to($recipient)->send(new TaskAssignedMail($taskTitle, $taskUrl))`.
**Data Shape:** `NotificationPreferences` is a readonly DTO over `array<string, array<string, bool>>` stored on `users.notification_preferences`; `wants($type, $channel) = overrides[$type->value][$channel->value] ?? $type->defaultEnabled($channel)` — TaskAssigned defaults in_app=true / email=false; TaskDigest defaults email=true.

### Decisive source
```php
$newIds = array_diff($currentIds, $previousAssigneeIds);

if ($newIds === []) {
    return;
}
...
defer(function () use ($newIds, $taskTitle, $taskId, $taskUrl): void {
    User::query()->whereIn('id', $newIds)->get()
        ->each(function (User $recipient) ...: void {
            if ($recipient->wantsNotification(NotificationType::TaskAssigned, NotificationChannel::InApp)) { ... }
            if ($recipient->wantsNotification(NotificationType::TaskAssigned, NotificationChannel::Email)) {
                Mail::to($recipient)->send(new TaskAssignedMail($taskTitle, $taskUrl));
            }
        });
});
```
The URL is resolved defensively BEFORE deferring: `TaskResource::getUrl('index', ['tableAction' => EditAction::getDefaultName(), 'tableActionRecord' => $task])` wrapped in `catch (\Throwable) { return '#'; }` — a route/tenant resolution failure degrades the link, never the save.

**Flow:** create/update task → diff current vs previous assignees → nothing new ⇒ no-op → snapshot payload → defer → HTTP response flushes → per-recipient channel gates decide database notification vs queued mail.
**Invariant:** Notification delivery is never inside the request's failure domain (deferred until after response), never repeats for unchanged assignments (diff gate), and each channel is independently suppressible by user preference with enum-declared defaults. A broken URL must not fail the task save.
**Probe:** `tests/Feature/Notifications/TaskAssignedEmailTest.php` — email queued only when the email channel is explicitly on; nothing queued by default; in-app notification skipped when `in_app => false`; `defer()->invoke()` flushes the deferred work inside the test.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "NotifyTaskAssignees previousAssigneeIds defer wantsNotification sendToDatabase TaskAssignedMail", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the diff gate (previous-ids parameter) for any assignment-style fan-out and the defer/response-detached side-effect pattern where your runtime supports it (queue the work instead where it does not). Adopt the preference-DTO-with-enum-defaults shape so "on by default" is declared next to the type, not scattered at call sites. Adapt channel names and the in-app notification renderer. Omit the Filament notification actions if you have no panel. Companion to `task-digest-timezone-banding.md` (same NotificationType/Channel gates).
