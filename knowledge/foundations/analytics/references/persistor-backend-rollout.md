<!-- capsule-v2 -->
# Persistor backend ladder — percent-gated rollout between embedded writes and a remote relay

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** How can one ingestion fleet run two persistence backends simultaneously without splitting traffic unpredictably?

## phash2 percent gate keyed on user_id
**Path/Symbol:** `lib/plausible/ingestion/persistor.ex:persist_event` (:8-13), `backend/2` (:15-38).
**Signature:** `backend(nil, user_id)`: if configured `backend == Embedded` OR `percent_enabled >= 100` → new backend; else `:erlang.phash2(user_id, 100) + 1 <= percent_enabled` → new backend; else fallback `Embedded`.
**Data Shape:** app env `:plausible, Plausible.Ingestion.Persistor` → `[backend: module, backend_percent_enabled: 0..100]`; opts may force `[:backend | rest]` override (tests/replay).
**Flow:** Event pipeline's `register_session` step → `Persistor.persist_event(event, previous_user_id, opts)` → chosen backend implements `persist_event/3`.
**Invariant:** (1) The gate hashes USER id, so every event of one visitor takes the same path — session state stays coherent across the boundary; (2) `Embedded` is always the safe default because it works on any single node (in-app buffers + local ClickHouse); remote variants need cluster infra.
**Probe:** `grep -n 'phash2(user_id, 100)' lib/plausible/ingestion/persistor.ex` → :30.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", qn_pattern: "ingestion.persistor$", fields: ["lines"], limit: 8 });
```

## Backend family
**Path/Symbol:** `lib/plausible/ingestion/persistor/embedded.ex` (40L), `embedded_with_relay.ex` (86L), `remote.ex` (:163L).
**Flow (embedded):** CacheStore.on_event → Session.WriteBuffer.insert + Event buffer insert — everything in-process. Relay twin adds forwarding to a relay service after local buffering; remote sends to another node entirely.
**Invariant:** All three must emit identical telemetry (`persistor/telemetry_handler.ex`, 177L) and identical `{:ok, event} | {:error, reason}` shapes — drop reasons like `:persist_timeout|:persist_error|:persist_decode_error` in the Event type are the contract surface.
**Probe:** `ls lib/plausible/ingestion/persistor/` → 4 files incl. telemetry_handler.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", file_pattern: "ingestion/persistor/*.ex", limit: 10 });
```

## Verdict
Adopt hash-percent rollout with an always-safe default backend; adapt percentages/flags; omit relay/remote twins unless running the same split topology.
