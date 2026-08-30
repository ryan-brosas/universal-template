<!-- capsule-v2 -->
# Consent-stamped workspace access — how does OAuth consent refuse a workspace that cannot use the API, and how does the chosen team reach the auth-code row Passport writes?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** When consent must both validate the selected workspace against billing health and hand the choice to a framework-controlled persistence point, where does the validation live and what carries the value across the boundary you do not own?

## Approve-controller gate + session-stash + creating-hook pull
**Path/Symbol:** `app/Http/Controllers/Mcp/ApproveAuthorizationController.php` (`approve`, 54L); `app/Models/Passport/AuthCode.php` (`booted`, 37L); `app/Services/Billing/HostedWorkspaceAccess.php` (`allows`/`isPaused`, 43L).
**Signature:** controller: `validate(['team_id' => ['required','string','size:26']])` → `Team::find` → `abort_if(! $user->belongsToTeam($team), 403)` → `abort_if($this->access->isPaused($team), 402)` → `session()->put('mcp.oauth.team_id', ...)` → `parent::approve(...)`. Model hook: `self::creating(fn ($code) => $code->team_id = session()->pull('mcp.oauth.team_id'))` when the stash is a non-empty string.
**Data Shape:** `allows` ladder (first hit wins): Billing feature off → `hosted_free_grandfathered_at !== null` → `subscription()?->valid() === true` → `plan === Enterprise` → `onGenericTrial()`; then `trial_ends_at !== null` (an EXPIRED trial) is explicitly false, and plain Pro is the final allow.

### Decisive source
```php
// A paused workspace answers 402 on every MCP call, so approving here would mint
// a token that can never do anything. Refuse at consent rather than hand the user
// a connector that silently fails on first use.
abort_if($this->access->isPaused($team), 402, 'This workspace is paused. ...');
$request->session()->put('mcp.oauth.team_id', $team->getKey());
```
```php
self::creating(function (self $code): void {
    $teamId = session()->pull('mcp.oauth.team_id');
    if (is_string($teamId) && $teamId !== '') {
        $code->team_id = $teamId;
    }
});
```

**Flow:** consent POST validates the ULID-shaped `team_id` (size 26, not an exists-rule — the find+abort gives a distinct 422 message) → membership and billing-health gates run BEFORE any state change → the team id is stashed in the session → Passport's standard approve flow persists the auth code → the custom AuthCode model's `creating` hook PULLS the stash (single-use; cannot leak into a later consent) and stamps `team_id`; a missing stash (code created outside the consent flow) leaves team_id null, which the downstream token middleware later rejects as malformed. Downstream consumer: `CopyTeamIdToAccessToken` (see `token-bound-team-context.md`) reads the auth-code row the hook stamped.
**Invariant:** Validation happens before delegation, never inside the framework flow you do not own. The session stash is pull-once. An expired trial is treated as WORSE than never-trialed Pro (explicit false rung before the final Pro allow) — a port that folds the two cases together re-opens paid access to churned trials. A workspace that cannot answer 200 on API calls must be refused at consent, not handed to the user as a silently failing connector.
**Probe:** `tests/Feature/Mcp/OAuthTeamPickerTest.php` — billing-paused workspace unselectable in the picker AND 402 on tampered submit; consent renders teams + capability disclosure; auth-code stamping end-to-end through the PKCE dance.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ApproveAuthorizationController HostedWorkspaceAccess isPaused AuthCode creating mcp.oauth.team_id grandfathered", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt refusing consent for workspaces that cannot use the resulting token, and the session-put / creating-hook-pull pair for passing a value into a framework-owned persistence point you cannot parameterize. Adopt the five-rung access ladder with the expired-trial-is-false distinction. Adapt Passport session mechanics and the Pennant feature gate to your auth/flag stack. Companion to `token-bound-team-context.md` (what happens to the stamped team id after the code is exchanged).
