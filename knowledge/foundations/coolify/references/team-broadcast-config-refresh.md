<!-- capsule-v2 -->
# Cross-tab config refresh via team-scoped broadcast event

## Source
Coolify `main@98116397`: `app/Livewire/Project/Shared/EnvironmentVariable/Show.php` (`submit`, :285-310), `app/Livewire/Project/Service/Configuration.php` (`getListeners`, :27-38), `app/Events/ApplicationConfigurationChanged.php` (whole file, 33L). Drift-introduced plane (upstream commit `50913dc4`); direct tests `tests/Feature/Livewire/ConfigurationCheckerTest.php` ("broadcasts a configuration update after a required service variable is set" + "refreshes the service configuration when a websocket configuration event arrives").

## Question
How does saving one required service variable refresh the Service Configuration page in EVERY open browser tab, including tabs on other machines?

## Path / Symbol
`Show::submit()` → `event(new ApplicationConfigurationChanged($teamId))`; `Configuration::getListeners(): array` returns dynamic Livewire listener map including an Echo private-channel key.

## Signature
```php
// Show.php :299-302 (after success/envsUpdated/configurationChanged dispatches)
if ($this->is_required && $this->resource instanceof Service) {
    event(new ApplicationConfigurationChanged($this->resource->team()->id));
}
// Configuration.php :28-38
public function getListeners(): array {
    $teamId = auth()->user()->currentTeam()->id;
    return [
        'refreshServices' => 'refreshServices',
        'refresh' => 'refreshServices',
        'configurationChanged' => 'refreshServices',                       // same-page bus
        "echo-private:team.{$teamId},ApplicationConfigurationChanged" => 'refreshServices', // cross-tab bus
    ];
}
```

## Data Shape
Event carries `public ?int $teamId`; `broadcastOn()` → `PrivateChannel("team.{teamId}")` or `[]` when teamId resolves to null. Listener key grammar: `echo-private:<channel>,<event-class>` mapped to the component method.

## Decisive source
Two-tier dispatch: local `dispatch('configurationChanged')` covers same-page components; the ShouldBroadcast event covers remote sessions. The trigger is NARROW by design — only `is_required && resource instanceof Service` fires the broadcast (plain application vars rely on page-local refresh), keeping websocket noise near zero.

## Flow / Invariant
INVARIANTS:
1. `getListeners()` MUST be a method (not the static `$listeners` property) whenever the key embeds runtime state — the pre-fix property form couldn't know the team id.
2. The broadcast fires AFTER all local dispatches and only on the success path (inside try, after `syncData`).
3. Team resolution order in the event constructor: explicit arg wins; else authenticated user's currentTeam; else null → NO channel → silently unbroadcast (never crashes).
4. Same handler (`refreshServices`) serves both buses so local and remote updates converge identically.

## Probe (direct tests)
From repo root:
```bash
grep -c 'echo-private:team.{$teamId},ApplicationConfigurationChanged' app/Livewire/Project/Service/Configuration.php
grep -cn "instanceof Service" app/Livewire/Project/Shared/EnvironmentVariable/Show.php
grep -c 'new PrivateChannel("team.{$this->teamId}")' app/Events/ApplicationConfigurationChanged.php
sed -n '/broadcasts a configuration update after a required service variable/,/^});/p' tests/Feature/Livewire/ConfigurationCheckerTest.php | grep -c 'Event::assertDispatched'
```
Expect 1 / 1 / 1 / 1. (PHPUnit runner blocked honestly: no PHP binary in this clone.)

## Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-coolify","query":"getListeners configurationChanged refreshServices","limit":3}'
```
→ hits incl. `Configuration.refreshServices Method app/Livewire/Project/Service/Configuration.php 74-79`.

## Verdict
ADAPT — the narrow-trigger + dual-bus + dynamic-listener pattern ports to any websocket-backed UI (Echo → your pubsub); keep the "only required service vars broadcast" noise gate.
