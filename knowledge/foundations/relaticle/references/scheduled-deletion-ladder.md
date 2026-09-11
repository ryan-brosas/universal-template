<!-- capsule-v2 -->
# Scheduled-deletion ladder — day-window reminders over named scopes and contract-delegated purges

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you implement GDPR-style scheduled account deletion with grace period, exactly-once reminders, and a purge that stays swappable?

## Two scopes, one command, contract-delegated deletion
**Path/Symbol:** `app/Console/Commands/PurgeScheduledDeletionsCommand.php` (whole, 98L, `#[Signature('app:purge-scheduled-deletions')] handle(DeletesUsers $deletesUsers, DeletesTeams $deletesTeams)`); scopes on BOTH `app/Models/User.php` :156-171 and `app/Models/Team.php` :237-252; schedule/cancel actions `app/Actions/Jetstream/ScheduleTeamDeletion.php` (44L) and `CancelTeamDeletion.php` (21L).
**Signature:** `scheduledForDeletion` = `whereNotNull('scheduled_deletion_at')`; `expiredDeletion` = `whereNotNull(...)->where('scheduled_deletion_at', '<=', now())`. Purge: `chunkById(100)` over `expiredDeletion()`, each entity deleted inside its own `DB::transaction` via the injected Jetstream contract. Reminders: `whereBetween('scheduled_deletion_at', [startOfDay, endOfDay] of now()->addDays(config('relaticle.deletion.reminder_days_before')))` over `scheduledForDeletion()`.
**Data Shape:** `scheduled_deletion_at` nullable timestamp on users and teams; config knobs `relaticle.deletion.grace_period_days` and `relaticle.deletion.reminder_days_before`; factory state `UserFactory::scheduledForDeletion(int $daysFromNow = 30)` accepts negatives to force expiry in tests.

### Decisive source
```php
DB::transaction(function () use ($team): void {
    $team->forceFill(['scheduled_deletion_at' => now()->addDays(config('relaticle.deletion.grace_period_days'))])->save();
    $team->teamInvitations()->delete();
});
$this->cancelSubscription->execute($team);
$owner->notify(new TeamDeletionScheduledNotification($team));
```
Scheduling refuses personal teams with a ValidationException ("Personal workspaces cannot be deleted directly"), is owner-only (`throw_unless($user->ownsTeam($team), AuthorizationException::class)`), deletes outstanding invitations in the same transaction, then cancels billing and notifies OUTSIDE the transaction. Cancel is the mirror: null the timestamp, notify.

**Flow:** owner schedules → grace-period stamp + invitation cleanup in one transaction → subscription cancelled, owner notified → daily command run: purge expired users then teams (contract-delegated, per-row transactions, logged), then send reminders to every entity whose deletion date falls inside TODAY+N's day window → running daily sends exactly one reminder per entity.
**Invariant:** The reminder predicate is a DAY WINDOW, not a "not yet reminded" flag — idempotence comes from running the command daily and each date falling in exactly one window. Deletion behavior is injected via `DeletesUsers`/`DeletesTeams` contracts, so the destructive step is swappable and testable without touching the command. Purge and reminder phases are independent: a reminder failure never blocks purging.
**Probe:** `tests/Feature/Commands/PurgeScheduledDeletionsCommandTest.php` — expired user deleted, non-expired (15d) survives, expired team deleted, day-25 reminder sent to user and to team OWNER ONLY (member asserted not sent); plus the anonymization pin: purging a member nulls `participant_id`/`participant_type` on surviving teams' `agent_conversations` while the conversation row itself survives. `tests/Feature/Teams/ScheduleTeamDeletionTest.php` and `tests/Feature/Profile/ScheduleUserDeletionTest.php` cover the action layer; `tests/Feature/Middleware/CheckScheduledDeletionTest.php` covers the interstitial gate.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "purge-scheduled-deletions expiredDeletion scheduledForDeletion reminder_days_before DeletesTeams", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-scope split (scheduled vs expired) and the day-window reminder — it needs no reminder-state column and self-heals after missed runs only within the window. Adapt grace/reminder config names; keep deletion behind a contract so the actual data-destroying step can differ per deployment. Omit the invitation cleanup if invitations are cascade-deleted. The six `app/Notifications/*Deletion*` classes share one shape (queued mail, config-driven day count, owner-only for teams) — treat them as one template, not six seams.
