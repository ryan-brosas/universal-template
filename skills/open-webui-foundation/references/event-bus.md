<!-- capsule-v2 -->
# Typed event bus — how do you fan one validated domain event to pluggable sinks without leaking secrets or cross-sink failures?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How do you validate event names against a catalog, sanitize payloads once, and keep one failing sink from breaking the others?

## build_event + sink list dispatch
**Path/Symbol:** `backend/open_webui/events.py:publish_event` (1151-1179), `build_event` (989-1025), `EVENT_SINKS` (1148), `_sensitive/_sanitize` (941-965).
**Signature:** `async def publish_event(request_or_app, event: EventDefinition | str, *, actor=None, subject_id=None, subject_type=None, source='api', data=None, message=None) -> None`.
**Data Shape:** `Event` pydantic payload: `{schema, id: uuid4, event: 'resource.operation', resource, operation, created_at, instance_id, version, source, actor, subject, data, message}`. Sinks implement `async handle_event(app, event, request=None)`; `EVENT_SINKS = [EventFunctionSink(), WebhookEventSink(), NotificationEventSink()]`.

### Decisive source
\`\`\`python
def _sensitive(key: Any) -> bool:
    normalized = str(key).lower().replace('-', '_')
    return (
        normalized in SENSITIVE_KEYS
        or normalized.endswith('_token')
        or normalized.endswith('_secret')
        or normalized.endswith('_api_key')
        or normalized.endswith('_key')
    )

for sink in EVENT_SINKS:
    try:
        await sink.handle_event(app, event_payload, request=request)
    except Exception:
        log.exception('Event sink failed for %s', event_payload.event)
\`\`\`

and name validation inside `event_name`: unknown names raise `ValueError(f'Unknown event: {name}')` before any sink runs.
**Flow:** caller passes catalog name or definition → `build_event` validates the name, splits `resource.operation`, sanitizes data (recursive sensitive-key strip + long-string truncation) and reduces actor to `SAFE_ACTOR_FIELDS` → each sink schedules its own async delivery (plugin event functions w/ valves + signature introspection, filtered webhooks, notification subset).
**Invariant:** an unknown event name raises before dispatch; sink exceptions are logged, never propagated to the publisher or sibling sinks; sanitized fields never reach sinks.
**Probe:** no test runner at this HEAD — deterministic anchors: `grep -n "EVENT_SINKS = \\[EventFunctionSink(), WebhookEventSink(), NotificationEventSink()\\]" backend/open_webui/events.py` hits line 1148; `grep -n "Unknown event" backend/open_webui/events.py` hits the validator.

## Get live surrounding code
**Retrieve:**
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "create_event_emitter publish_event websocket session redis fanout", limit: 10, fields: ["signature", "name", "file"] });
\`\`\`

## Verdict
Adopt catalog-validated names, single sanitize point, fail-soft ordered sink iteration; adapt sink set and `Event` schema fields to your domain; omit webhook/notification specifics. Coverage caveat: none for events.py; note `dispatch_event_functions` is plugin-gated by `ENABLE_PLUGINS`.
