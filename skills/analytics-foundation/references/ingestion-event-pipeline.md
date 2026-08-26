<!-- capsule-v2 -->
# Ingestion event pipeline — ordered drop-gates, dual attr maps, and the 200ms UA-parse timeout

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** In what order does an event get enriched and dropped, and why do drops happen before expensive work?

## reduce_while pipeline with halt-on-drop
**Path/Symbol:** `lib/plausible/ingestion/event.ex:pipeline` (:137-158), `process_unless_dropped` (:160-168), `build_and_buffer` (:56-87).
**Signature:** pipeline is `[{step_name :: atom, (event, context -> event)}]`; every step returns `%__MODULE__{}`; `execute_step` wraps each in PromEx duration telemetry tagged with the step name.
**Data Shape:** `%Ingestion.Event{domain, site, clickhouse_event_attrs, clickhouse_session_attrs, dropped?, drop_reason, request, salts, changeset}`; ~16 typed drop reasons.

### Decisive source
```elixir
[
  drop_verification_agent:, drop_datacenter_ip:, drop_threat_ip:,
  drop_shield_rule_hostname:, drop_shield_rule_page:, drop_shield_rule_ip:,
  put_geolocation:,            # geo BEFORE country shield so country rule can judge
  drop_shield_rule_country:,
  put_user_agent:,             # Headless Chrome + UAInspector.Result.Bot => :bot
  put_basic_info:, put_source_info:, maybe_infer_medium:, put_props:,
  put_revenue:, put_salts:, put_user_id:, validate_clickhouse_event:,
  register_session:
]
```

**Flow:** spam-referrer check short-circuits BEFORE per-domain GateKeeper loop → allow/deny per domain → steps enrich two separate maps (event attrs vs session attrs) → validation materializes `%ClickhouseEventV2{}` via changeset (`apply_action` failure ⇒ `drop(:invalid)`) → register_session persists via Persistor.
**Invariant:** (1) Order encodes cost: free header checks first, geo/UA (file lookups) after shields that don't need them, salts+user_id hashing near the end; (2) `maybe_infer_medium` derives `(gclid)/(msclkid)` utm_medium only when utm_medium nil AND referrer_source matches — inference never overrides explicit tags; (3) drops are data, not exceptions — the pipeline continues for OTHER domains in the same request.
**Probe:** `grep -c 'defp drop_' lib/plausible/ingestion/event.ex` → 6 (:206/:219/:229/:239/:247/:255/:348 minus defp drop generic = verify at runtime); `test/plausible/ingestion/event_test.exs` covers bot/spam drops.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^build_and_buffer$", fields: ["lines"], limit: 4 });
```

## UA parsing is cached AND time-boxed
**Path/Symbol:** `lib/plausible/ingestion/event.ex:parse_user_agent` (:457-483).
**Signature:** `Plausible.Cache.Adapter.fetch(:user_agents, user_agent, fn -> parse_user_agent_safe(ua) end)` wrapping `Task.Supervisor.async_nolink` under a PartitionSupervisor + `Task.yield(task, @parse_user_agent_timeout = 200) || Task.shutdown(task)`.
**Data Shape:** on timeout: telemetry `[:plausible, :ingest, :user_agent_parse, :timeout]`, returns `{:error, :timeout}`, step leaves OS/browser attrs unset (session gets empty strings downstream).
**Invariant:** The nolink task under a partitioned supervisor prevents one pathological UA from killing or queueing ingestion — timeout converts a hang into a degraded-but-accepted event. Caching by raw UA string means the 200ms budget amortizes to zero for real traffic.
**Probe:** `grep -n '@parse_user_agent_timeout 200' lib/plausible/ingestion/event.ex` → :457.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^parse_user_agent_safe$", fields: ["lines"], limit: 3 });
```

## User identity = SipHash over rotating salts
**Path/Symbol:** `lib/plausible/ingestion/event.ex:generate_user_id` (:566-590); `lib/plausible/session/salts.ex:refresh/rotate` (:28-72).
**Signature:** `SipHash.hash!(salt, user_agent <> remote_ip <> domain <> root_domain(hostname) <> replay_session_id)`; salt state `{current, previous}` served from a `read_concurrency` ETS table refreshed every 90s; rotation keeps previous for lookup compatibility; DB rows older than 48h deleted.
**Flow:** `put_salts` step snapshots both salts onto the event; `register_session` computes `previous_user_id` with the PREVIOUS salt so CacheStore can find sessions created before rotation.
**Invariant:** (1) user_id is pseudonymous but stable within a salt epoch — losing the previous-salt fallback mid-rotation would split sessions for every visitor; (2) `get_root_domain` special-cases IP-literal hostnames (no PublicSuffix lookup) and "(none)"; (3) nil salt/domain ⇒ nil user_id ⇒ session creation still proceeds keyed only on cache misses.
**Probe:** `test/plausible/session/salts_test.exs:13` ("agent starts and responds with current and previous salt after rotation") pins the two-slot window.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", name_pattern: "^generate_user_id$|^rotate$", fields: ["lines"], limit: 5 });
```

## Verdict
Adopt ordered drop-before-enrich pipelines and salt-window identity; adapt gate set to your abuse surface; omit EE revenue/shield gates when porting CE.
