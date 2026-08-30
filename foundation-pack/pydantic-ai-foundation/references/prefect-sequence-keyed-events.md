<!-- capsule-v2 -->
# Prefect sequence-keyed event tasks — content-identical events must each fire, retries must replay

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/prefect/_durability.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Prefect dedupes task calls by cache key — but an agent's event stream can emit two IDENTICAL events (same text delta) in one run, and a flow retry must replay the SAME events it delivered before. How do you key per-event handler tasks so both hold? A porter will key by event content (second identical delta never fires) or by a random uuid (retry re-fires everything).

## Path / Symbol
`_durability.py` — `PrefectDurability` class (:36–67), config composition with `with_non_retryable_errors` (:113–121), bound tasks trio (:131–176), `_dispatch_event_stream_event` sequence ladder (:185–206), `_wrap_leaf_toolset` (:208–212), `wrap_model_request` model-id carry + DurableModel swap (:216–257), `in_durable_context = FlowRunContext.get() is not None` (:181–183).

## Signature
```python
sequence_key = f'pydantic_ai_event_sequence:{self.name}'
sequence = flow_context.task_run_dynamic_keys.get(sequence_key, 0)
assert isinstance(sequence, int)
flow_context.task_run_dynamic_keys[sequence_key] = sequence + 1
await event_stream_handler_task(event, sequence)     # task(name='Handle Stream Event', **cfg)
```

## Data Shape
`task_run_dynamic_keys` is Prefect's OWN per-flow-run counter store for task-call disambiguation — a namespaced counter there gets exactly the retry-lineage lifetime Prefect's task naming relies on: within one flow run, every event gets a distinct sequence → distinct cache key → each fires; on flow retry, the SAME run re-executes, reproduces the same numbers 0..N, and replays from cache.

### Decisive source — the comment is the contract (:194–199)
```python
# The sequence number makes content-identical events within one flow run each fire
# (distinct task-cache keys) while a flow retry that re-executes the same run
# reproduces the same numbers and replays from cache. `task_run_dynamic_keys` is
# Prefect's own per-flow-run counter store ...
```
Model events ride INSIDE the model-request task (`capture_event_stream` runs the handler live there); only graph-level events take the per-event `Handle Stream Event` task. Config composition: `default_task_config | override`, wrapped with non-retryable error types for model/handler tasks because a framework misconfiguration (unrebuildable model) can't be fixed by retrying (:113–115).

**Flow:** graph event → dispatch → bump namespaced counter under the CURRENT FlowRunContext → call handler task(event, seq) → Prefect keys the call by inputs incl. seq → side effects checkpointed once per event per run, replayed identically on retry.

**Invariant:** Event-delivery idempotency must be keyed by (run identity, deterministic position) — NEVER by event value equality or wall-clock; counters must live in the engine's own per-run namespace so their lifetime matches the engine's replay semantics.

**Probe:** `tests/test_prefect.py` asserts `Handle Stream Event-\w+` task names appear once per event across multiple delivery sites (:395–667); `test_prefect_durability_event_stream_handler_rejects_enqueue` (:3005) pins the durable-task handler path end to end.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'PrefectDurability _dispatch_event_stream_event task_run_dynamic_keys'
```

## Verdict
**Adopt** the engine-native dynamic-key counter pattern for any at-least-once task framework whose cache keys derive from inputs. **Adapt** the namespace/key format to your engine's store. **Omit** the Prefect-specific config fields.
