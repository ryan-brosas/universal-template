<!-- capsule-v2 -->
# Docker label parsing survives commas and value-less entries

## Source
Coolify `main@98116397`, `bootstrap/helpers/docker.php` (`format_docker_labels_to_json`, :156-178). Drift-introduced fix #11477 (upstream commit `3da7f5a5`); direct test `tests/Unit/Api/LogEndpointHelpersTest.php:97-108`.

## Question
How must `docker ps --format '{{.Labels}}'` output be parsed so Traefik-style labels containing commas (and labels with no `=` at all) don't corrupt the container-label map?

## Path / Symbol
`format_docker_labels_to_json(string|array $rawOutput): Collection` — bootstrap/helpers/docker.php:156-178.

## Signature
```php
function format_docker_labels_to_json(string|array $rawOutput): Collection
// array input passes through untouched; string = docker ps stdout,
// one line per container, labels comma-separated inside one line.
```

## Data Shape
Per line: `"rule=Host(\`a.com\`,\`b.com\`),coolify.name=app-uuid"` → split on `,` FIRST (token level), then split each token on `=` with limit 2. Output: one Collection per line of `label => value`; only line `[0]` is returned (caller inspects a single container).

## Decisive source
```php
return collect($outputArray)
    ->mapWithKeys(function ($outputLine) {
        $label = explode('=', $outputLine, 2);
        if (count($label) !== 2) {
            return [];
        }
        return [$label[0] => $label[1]];
    });
```
(Pre-fix code did `explode('=')` then indexed `$outputLine[1]` — a comma inside a Host rule produced fragments like `\`b.com\`` with no `=`, and `$outputLine[1]` was either a wrong fragment or an undefined-index.)

## Flow / Invariant
INVARIANTS a porter must keep:
1. **Comma-split before equals-split** — commas separate labels even when they appear INSIDE another label's value (Traefik Host rules are backtick-comma lists).
2. **`= explode` uses limit 2** — values containing `=` (base64, URLs) keep their remainder intact.
3. **Value-less tokens yield NOTHING, not an entry** — returning `[]` from `mapWithKeys` skips the key entirely; a null-value entry would break downstream `filterServiceSubContainersByName` matching.
4. Array passthrough short-circuit: already-decoded input never re-splits.

## Probe (direct tests)
From repo root:
```bash
grep -n "explode('=', \$outputLine, 2)" bootstrap/helpers/docker.php
grep -c 'count($label) !== 2' bootstrap/helpers/docker.php
sed -n '97,108p' tests/Unit/Api/LogEndpointHelpersTest.php | grep -c 'another Docker label contains commas'
```
Expect 1 / 1 / 1. Runner caveat: PHPUnit not provisioned in this clone (no PHP on host) — expectations above verified byte-exact against the pin's sources.

## Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-coolify","query":"format_docker_labels_to_json","limit":3}'
```
→ rank-1 `ext-coolify.bootstrap.helpers.docker.format_docker_labels_to_json Function bootstrap/helpers/docker.php 156-178`.

## Verdict
ADOPT verbatim (algorithm is framework-free PHP; port the split-order + skip-empty contract to any language).
