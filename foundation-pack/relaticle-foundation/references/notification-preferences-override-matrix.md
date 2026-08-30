<!-- capsule-v2 -->
# Notification preferences override matrix — how does a per-cell preference UI stay in sync with the gates that consume it, without storing defaults?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you persist per-user, per-type, per-channel notification toggles so the settings UI and every notification sender read the SAME truth, while code-level defaults can still evolve?

## Overrides-only storage behind one shared predicate
**Path/Symbol:** `app/Livewire/App/Notifications/ManageNotificationPreferences.php` (whole, 78L); `app/Actions/User/UpdateNotificationPreferences.php` (whole, 22L); `app/Filament/Pages/NotificationPreferences.php` (38L page shell); `app/Enums/Notifications/NotificationGroup.php` (11L).
**Signature:** `mount()` hydrates `cells[type][channel] = $user->wantsNotification($type, $channel)` over `NotificationType::collaboration()` × `$type->channels()`; `updatedCells(bool $value, string $key)` parses the dotted `type.channel` key, re-validates both halves with `NotificationType::tryFrom` / `NotificationChannel::tryFrom` (malformed keys silently ignored), then `persist()` → `UpdateNotificationPreferences::execute($user, $type, $channel, $enabled)`.
**Data Shape:** the action builds the full `NotificationPreferences` DTO via `$user->notificationPreferences()->with($type, $channel, $enabled)` and stores ONLY `$preferences->overrides` in the user's `notification_preferences` JSON column — `['task_assigned' => ['email' => true]]`, never the whole matrix.

### Decisive source
```php
public function execute(User $user, NotificationType $type, NotificationChannel $channel, bool $enabled): void
{
    $preferences = $user->notificationPreferences()->with($type, $channel, $enabled);

    $user->update(['notification_preferences' => $preferences->overrides]);
}
```

**Flow:** UI toggle → Livewire `updated*` hook → dotted-key parse + enum re-validation → action → DTO overlay (`overrides[type][channel] ?? NotificationType::defaultEnabled()`) → only the overrides map persisted. Consumers (`NotifyTaskAssignees`, digest command) call the same `wantsNotification()` the UI hydrated from, so UI and gates cannot drift. The digest toggle is a separate `digestEnabled` boolean because `TaskDigest` is not a collaboration type; `NotificationGroup` (`Collaboration` / `Digest`) is the enum that partitions the types.
**Invariant:** Defaults live in code (`NotificationType::defaultEnabled()`), never in the stored JSON — a default change retroactively applies to every user who never touched that cell, and a stored override survives default changes. A malformed or unknown dotted key must be ignored, never persisted.
**Probe:** `tests/Feature/Notifications/ManageNotificationPreferencesTest.php` — default hydration (`task_assigned.in_app` true, `.email` false, `digestEnabled` true), instant per-cell persistence observable through `wantsNotification`, digest toggle persistence, standalone page render. `tests/Feature/Notifications/NotificationPreferencesTest.php` — code defaults when `notification_preferences` is null; single-cell override stores exactly `['task_assigned' => ['email' => true]]`.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ManageNotificationPreferences updatedCells UpdateNotificationPreferences overrides wantsNotification NotificationGroup collaboration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt overrides-only persistence behind one shared predicate: hydrate the UI from the exact function the senders gate on, store just the delta, keep defaults in code. Adopt per-cell instant persistence via Livewire `updated*` hooks with enum re-validation of both key halves. Adapt the Livewire/Filament surface and the DTO shape to your framework; the group partition (collaboration vs digest) is product surface. Companion to `deferred-assignee-notification.md` (the per-channel gates this UI feeds) and `task-digest-timezone-banding.md` (the digest gate).
