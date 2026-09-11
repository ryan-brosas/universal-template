<!-- capsule-v2 -->
# Onboarding wizard cap exemption — how do you keep a tenant-creation wizard alive after its own action pushed the user to the ownership limit?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** The wizard's "copy invite link" button pre-creates the workspace, which consumes the last slot of the user's ownership cap — how does the SAME wizard run keep rendering instead of 404ing on its own next Livewire request?

## Session-scoped completing marker + mount-time reset
**Path/Symbol:** `app/Filament/Pages/CreateTeam.php` :51 `COMPLETING_SESSION_KEY = 'onboarding.completing_workspace'`, :65 `mount()`, :95 `canView()`, :344-389 copyInviteLink action, :489 `skipInvites()`, :517 `handleRegistration()`, :398 `generateHandleFrom()`.
**Signature:** `canView(): bool` (static — Filament re-checks on every hydrate() AND inside register()); marker stores the pre-created team key.
**Data Shape:** Cap read from `config('relaticle.workspaces.max_owned_per_user')` (default 10) by `TeamPolicy::create()` (`app/Policies/TeamPolicy.php` :36: `$user->ownedTeams()->count() < (int) config(...)`).

### Decisive source
```php
public static function canView(): bool
{
    if (session()->has(self::COMPLETING_SESSION_KEY)) {
        return true;
    }

    return parent::canView();
}
```
(:95-102). Docblock: "Filament re-checks this on every hydrate() and again inside register(). Once 'Copy invite link' has created the workspace, the user sits at the cap *because of this wizard*, so without this exemption the page 404s on its own next request and Livewire has nowhere to surface it: the form simply stops responding." mount() (:69) forgets the key FIRST — "a pre-created workspace belongs to the wizard run that made it, so a fresh visit always starts from the real cap" — so a stale marker cannot smuggle a brand-new wizard past the gate.

**Flow:** over-cap fresh visit → mount clears stale marker → canView false → notification explaining the limit + redirect (Filament's default is a bare 404 that reads as a broken link) → in-run copyInviteLink creates team via CreateTeamAction, sets marker to tenant key → hydrate/register re-checks pass via exemption → handleRegistration reconciles name/slug onto the PRE-CREATED team (array_filter with ARRAY_FILTER_USE_BOTH skipping null and unchanged values) and sends invites → afterRegister forgets the marker. skipInvites() (:489-494) exists because BOTH footer buttons used to call register() directly, sending invites the user just decided to skip: it zeroes `data['invites']` then registers.
**Invariant:** The exemption is scoped to one wizard RUN (session key), never a blanket cap bypass; every entry path into the page must clear or re-establish scope (mount forget / copyInviteLink put / afterRegister forget).
**Probe:** `tests/Feature/Onboarding/CreateTeamOnboardingTest.php` (:1101 finish-a-run-at-cap — copyInviteLink takes user to 3/3 then `call('register')` succeeds; :1132 stale marker must not survive a fresh visit; :1083 explains-the-limit-instead-of-bare-404; :1073 fourth workspace under default cap; :940 skip-sends-nothing vs :963 confirm-still-sends).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CreateTeam canView COMPLETING_SESSION_KEY copyInviteLink skipInvites", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt run-scoped session exemption for any self-limiting multi-step creation flow; adapt the cap source and notification copy; omit Relaticle's Filament tenancy specifics. Five direct tests pin both exemption polarities and the stale-marker reset.
