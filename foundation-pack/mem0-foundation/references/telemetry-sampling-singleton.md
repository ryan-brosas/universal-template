<!-- capsule-v2 -->
# Telemetry sampling singleton — how do you ship opt-out telemetry that never leaks IDs, never raises, and never forks clients?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how is anonymous telemetry sampled, redacted, and kept to one client per process?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/telemetry.py`: `_DEFAULT_SAMPLE_RATE = 0.1` (:32), `_parse_sample_rate` (:35-45), `_LIFECYCLE_EVENTS` (:53-55), `_sampling_before_send` (:58-73), `_get_oss_telemetry` double-checked-locking singleton (:155-174), `capture_event` never-raise wrapper (:192-220); ID encoding `process_telemetry_filters` in `mem0/memory/utils.py` (:227-242).
**Signature:** `capture_event(event_name, memory_instance, additional_data=None)`; `_sampling_before_send(msg) -> msg | None` (PostHog before_send hook).
**Data Shape:** hot-path events sampled at 10% (`MEM0_TELEMETRY_SAMPLE_RATE`); lifecycle events (`mem0.init`, `mem0.reset`, `mem0._create_procedural_memory`, `mem0.notice_displayed`, `$identify`) always fire; properties annotated with the live sample_rate.

### Decisive source
```python
# >= so that rate=0 drops everything and rate=1 keeps everything (random ∈ [0, 1)).
if not is_lifecycle and random.random() >= MEM0_TELEMETRY_SAMPLE_RATE:
    return None
# Annotate so PostHog dashboards can extrapolate true counts via 1/sample_rate.
properties["sample_rate"] = 1.0 if is_lifecycle else MEM0_TELEMETRY_SAMPLE_RATE
...
# Module-level client telemetry singleton ... No before_send — hosted
# MemoryClient traffic must never be sampled.
client_telemetry = AnonymousTelemetry()
```

**Flow:** env-parsed sample rate (never raises; out-of-range → default) → per-event: encode scope ids as MD5 hashes (`process_telemetry_filters` sends key NAMES + hashed ids only), attach class-name strings for vector_store/llm/embedder (module-qualified, no config payloads) → before_send drops unsampled hot events and stamps survivors → singleton Posthog client created under a lock with atexit shutdown.
**Invariant:** telemetry can never raise into the main flow (every path wrapped); distinct_id is the persistent anonymous UUID from `setup.get_or_create_user_id`, never user content; sampled analytics remain extrapolable because every event carries its own rate; two client classes exist — OSS (sampled) and hosted-client (never sampled) — conflating them either spams or starves analytics.
**Probe:** `tests/test_telemetry_sampling.py` + `tests/test_telemetry.py::TestTelemetrySingleton` (singleton reuse :177, cross-thread single creation :187, atexit-once :207, shutdown-clears :254); `tests/test_telemetry_aliasing.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_sampling_before_send capture_event process_telemetry_filters singleton", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt before_send-sampling + self-describing-rate + md5-id-encoding + double-checked singleton as one pattern; adapt destinations; omit PostHog specifics if you have another sink.
