<!-- capsule-v2 -->
# Option KV store — how do you persist runtime settings with per-request caching and a default-fallback contract?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How are DB-backed options read/written so hot paths (fetch heartbeat, alert latches) avoid per-call queries while defaults stay config-driven?

## Option model
**Path/Symbol:** `app/Option.php:35` (`set`), `:75` (`get`), `:145-196` (`getOptions`), `:199` (`remove`).
**Signature:** `set($name, $value): bool`; `get($name, $default = false, $decode = true, $use_cache = true)`; `getOptions(array $options, array $defaults = [], array $decode = []): array`.
**Data Shape:** single-row-per-key table `{name, value}`; values JSON-encoded (serialize() deliberately NOT used — comment :207-210 "not safe"); static in-request `self::$cache[]` memo; sentinel `CACHE_DEFAULT_VALUE` marks "missed but resolved".

### Decisive source
```php
// app/Option.php:145-172 — batch read: serve all from static cache if complete
foreach ($options as $name) {
    if (isset(self::$cache[$name])) {
        if (self::$cache[$name] == self::CACHE_DEFAULT_VALUE) {
            $default = $defaults[$name] ?? self::getDefault($name);   // config('options.defaults')
            $values[$name] = $default;
        } else {
            $values[$name] = self::$cache[$name];
        }
    }
}
if (count($values) == count($options)) { return $values; } else { $values = []; }
// miss → one whereIn query → maybeUnserialize each → cache even the DEFAULTS under sentinel
```
**Flow:** set() sanitizes name, normalizes null→'', clones objects, `firstOrCreate`s the row, short-circuits when serialized old == new (no write), then updates both row and static cache (:35-73). getDefault() falls back to a `config('options.defaults')` map so code ships sensible values without seeding rows.
**Invariant:** the cache is PER-PROCESS and never invalidated cross-process — long-running queue workers see stale options until restart unless callers use `$use_cache=false`. Sentinel-cached defaults mean a later DB insert becomes visible only after process restart too. Alert-latch patterns (`alert_fetch_sent`) depend on set()'s write-skipping idempotence. FetchMonitor reads TWO keys atomically-ish via getOptions() so period+heartbeat resolve in one query on cold path.
**Probe:** `grep -c "CACHE_DEFAULT_VALUE" app/Option.php` (= 5) and `grep -c "maybeSerialize" app/Option.php` (= 3; its pair `maybeUnserialize` also = 3).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "Option get set", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt sentinel-defaults batch reader + no-write-on-same-value setter + config fallback chain; adapt to your settings table; omit serialize() entirely (keep JSON) and document the worker-staleness tradeoff you accept. Direct tests: tests/Unit/ConfigTest.php covers adjacent config helpers, not Option itself — treat semantics as source-pinned only.
