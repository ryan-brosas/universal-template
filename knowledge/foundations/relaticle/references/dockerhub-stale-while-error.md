<!-- capsule-v2 -->
# Stale-while-error pull counter — how do you show a marketing metric that survives the upstream API being down, without overstating it?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** A Docker Hub pull counter feeds a homepage strip — what is the cache/fallback/rounding ladder so an outage shows stale truth instead of zero?

## DockerHubService remember + forever last-good + floor rounding
**Path/Symbol:** `app/Services/DockerHubService.php` :15 `getPullCount(...)`, :43 `getFormattedPullCount(...)`.
**Signature:** `getPullCount(string $namespace = 'manukminasyan', string $repo = 'relaticle', int $cacheMinutes = 60): int`; formatted twin returns `?string`.
**Data Shape:** Cache keys: `dockerhub_pulls_{ns}_{repo}` (TTL window) and `dockerhub_pulls_{ns}_{repo}_last_good` (Cache::forever).

### Decisive source
```php
return (int) Cache::remember($cacheKey, now()->addMinutes($cacheMinutes), function () use ($namespace, $repo, $lastGoodKey): int {
    try {
        $response = Http::get("https://hub.docker.com/v2/repositories/{$namespace}/{$repo}/");

        if ($response->successful()) {
            $pulls = (int) $response->json('pull_count', 0);
            Cache::forever($lastGoodKey, $pulls);

            return $pulls;
        }
        ...
} catch ...
    return (int) Cache::get($lastGoodKey, 0);
```
(:20-37) plus the display rule (:41 docblock: "Rounded down to the nearest thousand so the figure never overstates, e.g. 21,000+"; :47 `if ($pulls < 1000) return null;` hides the line entirely below a thousand).

**Flow:** hit TTL cache → miss: fetch → success: refresh last-good FOREVER + return → failure/exception: log + return last-good (0 if never fetched) → format: floor-to-thousand with `+` suffix; <1000 ⇒ null (caller omits the element).
**Invariant:** The displayed figure must never go DOWN due to an outage and never overstate: last-good is monotone-ish truth, rounding only ever rounds down. Two independent caches because the roles differ — TTL freshness vs outage insurance.
**Probe:** `tests/Feature/Profile/DockerHubServiceTest.php` (:16 21,987→"21,000+"; :22 412→null; :28 unreachable→null; :34 assertSentCount(1) proves caching; :44 sequence push-then-500 still "21,000+" after cache forget).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "DockerHubService getPullCount getFormattedPullCount last_good", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-key stale-while-error shape for any third-party vanity metric; adapt endpoint/parsing; omit nothing else — 53 lines, five direct tests covering every branch.
