<!-- capsule-v2 -->
# sse-event-stream-grammar — What is the wire format the client actually receives?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How do internal queue events become SSE frames, and what does "ping" look like on the wire?

## Mapping→`data:` frame, bare-str→`event:` frame, ping collapses to the literal string
**Path/Symbol:** `api/core/app/apps/base_app_generator.py:BaseAppGenerator.convert_to_event_stream` (:312-328); consumer `api/core/app/apps/workflow/generate_response_converter.py:WorkflowAppGenerateResponseConverter.convert_stream_*_response` (:44-116).
**Signature:** `convert_to_event_stream(generator: Mapping | Generator[Mapping | str]) -> Generator[str]`.
**Data Shape:** Mapping payloads → `f"data: {orjson_dumps(message)}\n\n"`; plain-string messages pass through as complete frames (e.g. `"ping"`); error chunks carry only `{event, workflow_run_id}` plus the error envelope; simple mode strips node detail via `to_ignore_detail_dict()`.

### Decisive source
```python
@classmethod
def convert_to_event_stream(cls, generator: Union[Mapping, Generator[Mapping | str, None, None]]):
    """Convert messages into event stream"""
    if isinstance(generator, dict):
        return generator
    else:
        def gen():
            for message in generator:
                if isinstance(message, Mapping | dict):
                    yield f"data: {orjson_dumps(message)}\n\n"
                else:
                    yield f"event: {message}\n\n"
        return gen()
```
```python
# generate_response_converter.py: ping is special-cased BEFORE generic dumps
match sub_stream_response:
    case PingStreamResponse():
        yield "ping"
        continue
    case ErrorStreamResponse():
        response_chunk = {"event": sub_stream_response.event.value, "workflow_run_id": chunk.workflow_run_id}
        response_chunk.update(cls._error_to_stream_response(sub_stream_response.err))
```

**Flow:** pipeline yields typed StreamResponse objects → converter matches: Ping→literal "ping" frame; Error→event+run-id+error envelope; NodeStart/Finish in simple mode→detail-stripped dump; everything else→full JSON dump with event + workflow_run_id injected at top level.
**Invariant:** Every non-ping frame carries `workflow_run_id` at TOP level even though it also exists inside data — clients rely on the outer field before parsing; ping bypasses JSON entirely (keepalive semantics); orjson is the serializer of record (compact, fast).
**Probe:** `grep -c 'orjson_dumps(message)' core/app/apps/base_app_generator.py` → 1; `grep -c 'yield \"ping\"' core/app/apps/workflow/generate_response_converter.py` → 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "convert_to_event_stream SSE data event orjson", limit: 10 });
```

## Verdict
Adopt the two-frame grammar and top-level run-id injection. Adapt the event vocabulary. Omit simple/full dual modes unless you serve both UI and API consumers from one stream.
