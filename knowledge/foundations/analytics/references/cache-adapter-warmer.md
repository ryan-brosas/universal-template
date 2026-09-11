<!-- capsule-v2 -->
# Partitioned ConCache Adapter + two-mode warmer — the caching substrate under sessions, salts, and UA parsing

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** How does Plausal-style code get a crash-tolerant, partition-sharded in-memory cache whose misses fall back to source-of-truth without changing callers?

## Adapter: every op wrapped in catch :exit
**Path/Symbol:** `lib/plausible/cache/adapter.ex:get` (:58-65), `get/3 dirty_get_or_store` (:68-75), `put_many` (:100-112), `get_name/2` (:161-170).
**Signature:** all public functions `catch :exit, _ -> Logger.error(...); nil|:ok|[]` — cache unavailability degrades to miss, never crashes ingestion.
**Data Shape:** partitions configured per-cache in `:plausible, Plausible.Cache.Adapter` env (`partitions: N`); partition chosen by `:erlang.phash2(key, partitions) + 1`, name derived `:"#{cache}_#{n}"`.

### Decisive source
```elixir
defp get_name(cache_name, key) do
  partitions = partitions(cache_name)
  if partitions == 1 do
    cache_name
  else
    chosen_partition = :erlang.phash2(key, partitions) + 1
    String.to_existing_atom("#{cache_name}_#{chosen_partition}")
  end
end
```

**Flow:** get → partition → ConCache; `put_many` groups items BY target partition then does one raw `:ets.insert(ConCache.ets(name), items)` per group — bypassing ConCache locking for bulk warm fills.
**Invariant:** (1) phash2 must match between `child_specs/3` (starts N named caches) and `get_name/2` (routes keys) — re-partitioning requires restart, not hot resize; (2) raw ETS insert skips TTL bookkeeping — only used for full-refresh paths where the warmer owns lifecycle.
**Probe:** `grep -c 'phash2' lib/plausible/cache/adapter.ex` → 2 (:167 route + none else).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^get_name$|^child_specs$", fields: ["lines"], limit: 4 });
```

## Behaviour with dual refresh modes
**Path/Symbol:** `lib/plausible/cache.ex` callbacks (:38-51), `refresh_all` vs `refresh_updated_recently` (:134-162), `merge_items` (:164-187), `ready?` (:196-213).
**Flow:** `refresh_all` runs base query + deletes stale keys (Set-difference old−new); `refresh_updated_recently` adds `where updated_at > ago(^15, "minute")` + merge WITHOUT deletion — cheap frequent cycle run alongside the heavy one by `Cache.Warmer` (:gen_cycle behaviour, hibernates between cycles).
**Invariant:** (1) When `Plausible.Cache.enabled?()` is false (default in tests), `get/2` falls back to `get_from_source/1` callback — callers never know; (2) multi-node coherence via `broadcast_put/broadcast_delete` through `:rpc.multicall` fired in a detached Task (5s timeout, fire-and-forget) — eventual consistency accepted.
**Probe:** `grep -c 'defoverridable' lib/plausible/cache.ex` → 4 (:113/:129/:132/:162).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", file_pattern: "^lib/plausible/cache.ex$", fields: ["lines"], limit: 10 });
```

## Verdict
Adopt partitioned-cache + exit-catching adapter + all/updated-recently refresh pair; adapt backend (ConCache→your ETS wrapper); omit rpc.multicall broadcasts for single-node ports.
