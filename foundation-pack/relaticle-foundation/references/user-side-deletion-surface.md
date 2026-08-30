<!-- capsule-v2 -->
# User-side deletion surface — ScheduleUserDeletion, CheckScheduledDeletion, interstitial

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How does a USER (not a team) schedule account deletion, and what keeps the panel locked while the grace period runs?

## Ownership-refusal gate then a two-row stamp
**Path/Symbol:** `app/Actions/Jetstream/ScheduleUserDeletion.php` (44L, `schedule(User $user): void`, `ensureUserCanBeDeleted()` :31-42); `app/Actions/Jetstream/CancelUserDeletion.php` (25L, `cancel(User $user): void`); middleware `app/Http/Middleware/CheckScheduledDeletion.php` (25L); page `app/Livewire/App/Profile/ScheduledDeletionInterstitial.php` (92L).
**Signature:** `ensureUserCanBeDeleted` collects `$user->ownedTeams()->where('personal_team', false)->whereHas('users')->pluck('name')` and throws `ValidationException::withMessages(['team' => ["Transfer ownership of these workspaces before deleting your account: ..."]])` when non-empty. Stamp: `now()->addDays(config('relaticle.deletion.grace_period_days'))` on the user AND `ownedTeams()->where('personal_team', true)` in one `DB::transaction`; notification sent AFTER commit.
**Data Shape:** `users.scheduled_deletion_at` nullable datetime (cast); `isScheduledForDeletion()` = `scheduled_deletion_at !== null` (User :146, Team :227 — same predicate both models); factory state `scheduledForDeletion(daysFromNow)` (negative ⇒ expired).

### Decisive source
```php
if ($user?->isScheduledForDeletion() && ! $request->routeIs('*.scheduled-deletion', 'scheduled-deletion', 'logout', '*.auth.logout')) {
    return to_route('filament.app.scheduled-deletion');
}
```
The allowlist is the invariant: the interstitial route itself (both `*.scheduled-deletion` and bare `scheduled-deletion` forms) and logout stay reachable — the gate locks browsing, never the exit. The interstitial's `mount()` bounces non-scheduled users to home/login, so gate and page agree in both directions; `cancelDeletion()` runs `CancelUserDeletion` (nulls user + personal team in one transaction), then re-resolves the tenant and redirects home. Join/invitation controllers add the same predicate as abort guards (`JoinTeamViaLinkController` :97/:101, `AcceptTeamInvitationController` :44 — 410 for scheduled teams, 403 for scheduled users), so the deletion state also blocks inbound membership changes.

**Flow:** schedule (refusal check → transaction stamps user + personal team → owner notified) → every panel request gated → interstitial offers cancel/logout only → cancel clears both stamps; expiry hands off to the purge command (see `scheduled-deletion-ladder.md`).
**Invariant:** The gate must never trap the user (self + logout always allowed); gate and page agree in both directions; a personal team's deletion date always equals its owner's; ownership of any staffed workspace blocks scheduling entirely; memberships in other teams survive the grace period.
**Probe:** `tests/Feature/Profile/ScheduleUserDeletionTest.php` — refusal when owning a staffed team (nothing stamped); personal team stamped alongside user; memberships retained; cancel clears both. `tests/Feature/Middleware/CheckScheduledDeletionTest.php` — redirect on/off, interstitial render, cancel-from-interstitial, redirect-host parity, logout.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ScheduleUserDeletion ensureUserCanBeDeleted CheckScheduledDeletion ScheduledDeletionInterstitial cancelDeletion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ownership-refusal gate (list the blocking workspaces by name) and the two-row stamp for user-initiated account deletion. Adopt the middleware allowlist (self + logout) and the both-directions gate/page agreement. Adapt route names, grace config key, and abort codes (410/403) to your framework. Omit the Filament tenant re-resolution if you have no multi-tenant panel. Companion to `scheduled-deletion-ladder.md` (team-side ladder + purge) and `scheduled-deletion-interstitial.md` (the same gate from the page's perspective — read both before porting; this capsule carries the action/refusal detail, that one the page/mount detail).
