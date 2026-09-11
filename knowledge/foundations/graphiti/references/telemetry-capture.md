<!-- capsule-v2 -->
# Telemetry capture — silent-by-design opt-out analytics beside OTel tracing

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how do you ship anonymous product telemetry in an OSS library so it can never break a user's run — and how does it coexist with (not replace) user-owned tracing?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/telemetry/telemetry.py:is_telemetry_enabled` (:29–37), `get_anonymous_id` (:40–62), `capture_event` (:92–117); sole call site `graphiti_core/graphiti.py:266 capture_event('graphiti_initialized', properties)` inside `_capture_initialization_telemetry` with provider detection via class-name sniffing (`_get_provider_type`).
**Signature:** `capture_event(event_name: str, properties: dict[str, Any] | None = None) -> None` — fire-and-forget, never awaited, never raises.
**Data Shape:** one event per Graphiti() construction carrying `{llm_provider, embedder_provider, reranker_provider, database_provider}` derived from `client.__class__.__name__.lower()` substring matching; anonymous id persisted at `~/.cache/graphiti/telemetry_anon_id`.

### Decisive source
```python
def is_telemetry_enabled():
    if 'pytest' in sys.modules:            # never phone home from tests
        return False
    env_value = os.environ.get('GRAPHITI_TELEMETRY_ENABLED', 'true').lower()
    return env_value in ('true', '1', 'yes', 'on')

# capture_event body: initialize_posthog() returns None on ImportError or ANY error;
# every stage wrapped so the outermost except swallows all exceptions silently.
event_properties = {'$process_person_profile': False,   # PostHog: no person profile
                    'graphiti_version': get_graphiti_version(),
                    'architecture': platform.machine(),
                    **(properties or {})}
```

**Flow:** import-time constants (public PostHog ingest key) → construction-time single event → env-var default-ON with four accepted truthy spellings → pytest-in-modules hard-off → anonymous UUID cached to a file so reinstalls don't fork identities.
**Invariant:** (1) telemetry NEVER throws into the host app — the entire chain is exception-swallowing by design; (2) it is a separate plane from `Tracer`/OpenTelemetry (user-owned performance traces) — do not merge them when porting; (3) missing posthog dependency = silently disabled, not an install requirement; (4) `$process_person_profile: False` keeps PostHog from creating person profiles from distinct_ids.
**Probe:** no unit test covers telemetry.py (coverage caveat — verified by whole-file read; its behavior is deliberately untestable-by-default because `'pytest' in sys.modules` disables it).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "capture_event is_telemetry_enabled posthog anonymous", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the never-throws fire-once-at-init shape and the test-detection kill switch; adapt the vendor/endpoint; omit entirely if your host forbids outbound calls — the library works identically without it.
