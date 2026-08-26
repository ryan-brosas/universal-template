<!-- capsule-v2 -->
# Session CacheStore — 30-minute latching, sign-pair updates, and per-user serialized dispatch

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** How does an incoming event find, update, or create its session — and what stops two events of one user from racing the read-modify-write?

## on_event flow under a balancer lock
**Path/Symbol:** `lib/plausible/session/cache_store.ex:on_event` (:16-47), `find_session` (:74-97), `handle_event` (:60-70).
**Signature:** `on_event(event, session_attributes, prev_user_id, opts) :: {:ok, session} | {:error, :timeout}`; `@lock_timeout 1000` ms.
**Data Shape:** cache key `{site_id, user_id}` (EE adds `replay_session_id`); lookup tries current salt user_id THEN previous-salt user_id (`prev_user_id`) so a mid-rotation visitor still resolves.

### Decisive source
```elixir
found = find_session(event, event.user_id) || find_session(event, prev_user_id)
...
if NaiveDateTime.diff(event.timestamp, session.timestamp, :minute) <= 30 do
  session   # else nil → new session
end
```

**Flow:** Balancer.dispatch(user_id) serializes per-user work → find in partitioned ConCache → 30-min latch decides continue-vs-new → engagement events only refresh timestamp (`refresh_session_cache`, never writes rows) → otherwise write sign-pair `[old(sign:-1), updated(sign:+1)]` and dirty-put updated session back.
**Invariant:** (1) The −1/+1 pair is ONE buffered insert list — atomicity comes from ClickHouse row order, not a transaction; (2) timeout is fail-open for ingestion (event dropped as `:lock_timeout`, telemetry to Sentry) rather than blocking the pipeline; (3) engagement-with-no-session returns `:no_session_for_engagement` drop reason instead of fabricating a session.
**Probe:** `test/plausible/session/cache_store_test.exs:39` ("event processing is sequential within session"), `:381` ("keeps session in cache after engagement events").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^on_event$|^update_session$", fields: ["lines"], limit: 5 });
```

## Session field-update rules encode dashboard semantics
**Path/Symbol:** `lib/plausible/session/cache_store.ex:update_session` (:121-149).
**Data Shape:** entry_page/hostname latch on FIRST pageview (`== ""` guard means non-pageview first events leave them empty); exit_page/hostname overwritten on EVERY pageview; is_bounce flips off when `pageviews ≥ 2` OR a non-pageview interactive event arrives; duration = `|timestamp - start|`.
**Invariant:** Bounce definition is behavioral ("second pageview or any interactive non-pageview event"), not time-based — a porter implementing time-window bounces changes every bounce_rate number. The `entry_page == ""` re-check makes entry sticky even if the first pageview was dropped upstream.
**Probe:** `test/plausible/session/cache_store_test.exs:207` ("creates a session from an event") + `:366` ("does not update session counters on engagement event") pin creation vs refresh.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", qn_pattern: "session.cache_store", fields: ["lines"], limit: 12 });
```

## Balancer: phash2 sharding over N GenServers replaces locks
**Path/Symbol:** `lib/plausible/session/balancer.ex:dispatch` (:14-25); `lib/plausible/session/balancer_supervisor.ex:size` (100 workers prod, 10 test).
**Signature:** `worker = :erlang.phash2(user_id, size()) + 1; [{pid,_}] = Registry.lookup(Registry, worker); GenServer.call(pid, {:process, fun}, timeout)`.
**Data Shape:** same user_id always lands on the same worker GenServer; the fun executes inside `handle_call`, so per-user calls queue behind each other — serialization without keys or mutexes.
**Invariant:** Cross-worker concurrency remains possible if user_id hashing changes between nodes (rolling deploys) — the design accepts rare races rather than distributed locks. `local?: true` bypasses dispatch entirely (tests/replay).
**Probe:** `grep -c 'phash2' lib/plausible/session/balancer.ex lib/plausible/cache/adapter.ex` → 1 each (same idiom, two planes).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^dispatch$", fields: ["lines"], limit: 4 });
```

## Verdict
Adopt hash-sharded actor serialization + sign-pair updates; adapt the 30-minute latch to your session policy; omit EE replay_session_id key extensions.
