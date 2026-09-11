<!-- capsule-v2 -->
# Scheduled-deletion interstitial — hard middleware gate with an always-open exit

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you lock a scheduled-for-deletion user out of the product while guaranteeing they can always cancel or log out — and keep the personal workspace from outliving the account?

## Panel-wide gate + standalone interstitial page
**Path/Symbol:** `app/Http/Middleware/CheckScheduledDeletion.php` (whole, 25L, `handle(Request $request, Closure $next): Response`); page `app/Livewire/App/Profile/ScheduledDeletionInterstitial.php` (92L, `mount()` :20-36, `cancelDeletion()` :39-56); actions `app/Actions/Jetstream/ScheduleUserDeletion.php` (44L, `schedule(User $user): void`), `app/Actions/Jetstream/CancelUserDeletion.php` (25L); registration `app/Providers/Filament/AppPanelProvider.php` :271-273 (route) + :306 (authMiddleware).
**Signature:** middleware `if ($user?->isScheduledForDeletion() && ! $request->routeIs('*.scheduled-deletion', 'scheduled-deletion', 'logout', '*.auth.logout')) return to_route('filament.app.scheduled-deletion');`. `isScheduledForDeletion()` = `scheduled_deletion_at !== null` (User :146 and Team :227 — same predicate on both models).
**Data Shape:** `users.scheduled_deletion_at` / `teams.scheduled_deletion_at` nullable datetime; grace period `config('relaticle.deletion.grace_period_days')`; factory state `scheduledForDeletion(daysFromNow)` (negative values drive expiry in tests).

### Decisive source
```php
DB::transaction(function () use ($user): void {
    $deletionDate = now()->addDays(config('relaticle.deletion.grace_period_days'));

    $user->forceFill(['scheduled_deletion_at' => $deletionDate])->save();

    $user->ownedTeams()
        ->where('personal_team', true)
        ->update(['scheduled_deletion_at' => $deletionDate]);
});
```
Precondition `ensureUserCanBeDeleted()` refuses with a ValidationException listing names when the user owns any NON-personal team that still has members (`ownedTeams()->where('personal_team', false)->whereHas('users')->pluck('name')`) — ownership must be transferred first. Cancel mirrors the transaction (nulls user + personal team). The interstitial's `mount()` bounces non-scheduled users to home/login, so gate and page agree in BOTH directions; `cancelDeletion()` resolves the tenant, `Filament::setTenant($tenant)`, and redirects home.

**Flow:** schedule (refusal check → transaction stamps user + personal team → owner notified) → every panel request hits the middleware → scheduled user lands on the interstitial for everything except the interstitial route itself and logout → cancel (or grace expiry, then the purge command from `scheduled-deletion-ladder.md`).
**Invariant:** The gate must never trap the user: the interstitial and logout routes are always reachable. The gate and the page must agree in both directions (middleware redirects scheduled users in; mount bounces unscheduled users out). A personal team's deletion date always equals its owner's — the workspace cannot outlive the account. Membership in OTHER teams is retained during grace (test-pinned).
**Probe:** `tests/Feature/Middleware/CheckScheduledDeletionTest.php` — redirect on/off; interstitial renders "Your account is being deleted"; cancel from interstitial nulls `scheduled_deletion_at`; redirect host == interstitial host; logout works. `tests/Feature/Profile/ScheduleUserDeletionTest.php` — refusal when owning a staffed team (and nothing stamped); personal team stamped alongside user; memberships retained during grace; cancel clears both.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CheckScheduledDeletion ScheduledDeletionInterstitial isScheduledForDeletion routeIs scheduled-deletion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the middleware-gate-plus-interstitial shape with the explicit route allowlist (self + logout) for any "account is being closed" state, and the stamp-user-and-personal-workspace-together transaction. Adopt the both-directions agreement rule (gate redirects in, page bounces out) — it prevents the classic dead redirect loop. Adapt route names, grace config key, and the refusal message. Omit the Filament tenant plumbing if you have no multi-tenant panel. Companion to `scheduled-deletion-ladder.md` (team-side schedule/cancel + purge command) — this capsule is the user-side surface of the same ladder.
