<!-- capsule-v2 -->
# Restart-required vs update-available: split proxy status labels

## Source
Coolify `main@98116397`, `resources/views/components/server/status-summary.blade.php` (:9-20 php block + :75 label render). Drift-introduced fix (upstream commit `98116397`). Direct test `tests/Feature/ServerStatusIndicatorDesignTest.php` (+4 assertions pinning the match arms verbatim).

## Question
Why must a pending proxy CONFIGURATION restart and an available proxy IMAGE update render as different labels even though both set the warning color?

## Path / Symbol
Blade component locals `$proxyConfigurationPending` / `$traefikUpdateAvailable` / `$proxyStatusLabel`; model predicates `hasPendingProxyConfiguration()` vs `hasCurrentTraefikOutdatedInfo()`.

## Signature
```blade
$proxyConfigurationPending = $server->proxySet() && $server->hasPendingProxyConfiguration();
$traefikUpdateAvailable    = $server->proxySet() && $server->hasCurrentTraefikOutdatedInfo();
$proxyUpdateAvailable      = $proxyConfigurationPending || $traefikUpdateAvailable; // attention logic UNCHANGED
$proxyStatusLabel = match (true) {
    $proxyConfigurationPending => 'Restart required',
    $traefikUpdateAvailable    => 'Update available',
    default                    => str($proxyStatus ?: 'unknown')->headline(),
};
...
<span>{{ $proxyStatusLabel }}</span>   @* was: str($proxyStatus ?: 'unknown')->headline() *@
```

## Data Shape
Two booleans collapse three display states into two labels + fallback; precedence is encoded by match-arm ORDER (pending beats outdated).

## Decisive source
Pre-fix both conditions shared one aggregate (`$proxyUpdateAvailable`) and the UI printed only the runtime status headline — a queued config change looked identical to a new Traefik version, so operators restarted when they should have updated and vice versa. The fix splits the SIGNALS while deliberately keeping the ATTENTION computation (`$proxyNeedsAttention` / summary match) consuming the same OR-aggregate — behavior-neutral for colors, decisive for text.

## Flow / Invariant
INVARIANTS:
1. Precedence: configuration-pending wins the label over image-update (match arm order).
2. The aggregate boolean stays as-is for attention/coloring — only the LABEL channel got a second signal source; don't refactor the coloring onto the split booleans.
3. Fallback remains runtime-status headline (`running` → "Running"); null status → "unknown".
4. The design test asserts blade SOURCE STRINGS (toContain on file contents) — the exact arm texts `'Restart required'` / `'Update available'` are contract, not incidental copy.

## Probe (direct tests)
From repo root:
```bash
grep -c "\$proxyConfigurationPending => 'Restart required'" resources/views/components/server/status-summary.blade.php
grep -c "\$traefikUpdateAvailable => 'Update available'" resources/views/components/server/status-summary.blade.php
grep -c '{{ $proxyStatusLabel }}' resources/views/components/server/status-summary.blade.php
```
Expect 1 / 1 / 1. (PHPUnit runner blocked honestly.)

## Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-coolify","query":"proxyStatusLabel restart required update available","limit":3}'
```
→ BM25 hits in `resources/views/components/server/status-summary.blade.php` (Section node; doc-shaped files resolve via body tokens here).

## Verdict
ADAPT — keep the two-signal/two-label + shared-aggregate shape; rename predicates for your stack.
