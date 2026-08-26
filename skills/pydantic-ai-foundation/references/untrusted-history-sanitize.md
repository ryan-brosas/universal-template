<!-- capsule-v2 -->
# Untrusted-history sanitization — what must be stripped from client-submitted messages before an agent will run them?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Which parts of browser-supplied history are injection or IAM-risk vectors, and in what order does the sanitizer remove them so no empty-message or dangling-call hole remains?

## `sanitize_messages` + `_strip_dangling_tail_tool_calls` + `_sanitize_tool_return_content`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/messages.py:sanitize_messages` (:2937–3119), `_strip_dangling_tail_tool_calls` (:3122–3157), `_drop_compaction_parts` (:2912–2934), `_filter_user_content` (:3215–3246), `_sanitize_tool_return_content` (:3264–3330), `_sanitize_response_parts` (:3333–3383).
**Signature:** `sanitize_messages(messages, *, strip_system_prompts=True, strip_compaction_parts=False, allowed_file_url_schemes=('http','https'), allowed_file_url_force_download=(), allow_uploaded_files=False, resolved_tool_call_ids=()) -> list[ModelMessage]`.
**Data Shape:** Drops (never empties) messages whose parts all sanitize away; collects per-category warning sets (`disallowed_url_schemes`, `reset_force_download_values`, `dropped_uploaded_file_providers`, `dangling_tool_call_names`) and emits one UserWarning per category at the end.

### Decisive source
```python
# messages.py:3145-3157 — the tail is only known AFTER empty messages are dropped
while sanitized and isinstance(tail := sanitized[-1], ModelResponse):
    kept_parts = []
    for part in tail.parts:
        if isinstance(part, ToolCallPart) and part.tool_call_id not in resolved_tool_call_ids:
            dangling_names.append(part.tool_name)
        else:
            kept_parts.append(part)
    if len(kept_parts) == len(tail.parts):
        break
    if kept_parts:
        sanitized[-1] = replace(tail, parts=kept_parts)
        break
    sanitized.pop()
```

**Flow:** optional `_drop_compaction_parts` first (client boundary would hide trusted server-side history) → per-request: strip SystemPromptParts (the system prompt is the server's to own; a client that injects one overrides agent behavior), filter user content file URLs by scheme allowlist + reset non-allowed `force_download`, drop UploadedFile unless opted in → per-response: strip the compaction provenance stamp from provider_details, recursively sanitize FileUrl/UploadedFile nested anywhere in tool-return content → THEN walk trailing responses stripping unresolved tool calls (keeping ids in `resolved_tool_call_ids` for same-request HITL resume) → warn once per category.

**Invariant:** The tail walk MUST anchor on post-drop history: a trailing request that sanitized to empty is gone, which can re-expose an earlier response whose tool calls a promptless run would dispatch — anchoring on pre-drop indexes misses it. NativeToolCallParts stay: providers execute them server-side and pair each with a return, and the agent loop never dispatches them. Narrower subclasses (`tool_kind` set) are skipped during content sanitization because their typed TypedDict content has required fields a stripped key would invalidate. Non-HTTP schemes (`s3://`, `gs://`) make the PROVIDER fetch objects with server-side IAM roles; `'allow-local'` opts out of SSRF private-IP blocking — both default-deny from untrusted clients.

**Probe:** `tests/test_sanitize_messages.py::test_sanitize_messages_resets_force_download_from_serialized_history` (:30), `..._strips_dangling_call_exposed_by_dropped_tail` (:162), `..._keeps_resolved_call_exposed_by_dropped_tail` (:182), `..._strips_dangling_call_but_keeps_other_tail_parts` (:199), `..._drops_empty_response` (:219), `..._strips_compaction_provenance_stamp` (:103), `..._strips_compaction_parts_for_mixed_custody` (:140), plus scheme/upload tests :244-290.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "sanitize_messages _strip_dangling_tail_tool_calls _sanitize_tool_return_content _drop_compaction_parts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the strip-order (compaction custody → system prompts → schemes/force-download/uploads → recursive tool-return walk → post-drop tail resolution) and every default-deny. Adapt allowlists per deployment trust model. Omit nothing — the ordering constraints between drops and the tail walk are exactly what a naive reimplementation gets wrong.
