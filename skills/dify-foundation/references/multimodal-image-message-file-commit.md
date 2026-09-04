<!-- capsule-v2 -->
# multimodal-image-message-file-commit — How do generated images become first-class message attachments?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What is the persistence + notification path for images an LLM returns mid-stream?

## Independent session, commit BEFORE publish, fail-open to log
**Path/Symbol:** `api/core/app/apps/base_app_runner.py:AppRunner._handle_multimodal_image_content` (:371-457); caller arm in `_handle_invoke_result_stream` (:316-340).
**Signature:** `_handle_multimodal_image_content(content: ImagePromptMessageContent, message_id, user_id, tenant_id, queue_manager, session) -> str | None`.
**Data Shape:** Input = image URL or base64 (data-URL prefix stripped); output row `MessageFile(type=IMAGE, transfer_method=TOOL_FILE, belongs_to=ASSISTANT, url=/files/tools/{tool_file.id}, upload_file_id)`; success publishes `QueueMessageFileEvent(message_file_id)`.

### Decisive source
```python
if not image_url and not base64_data:
    _logger.warning("Image content has neither URL nor base64 data")
    return None
tool_file_manager = ToolFileManager()
try:
    if image_url:
        tool_file = tool_file_manager.create_file_by_url(user_id=user_id, tenant_id=tenant_id,
                                                         file_url=image_url, conversation_id=None)
    elif base64_data:
        if base64_data.startswith("data:"):
            base64_data = base64_data.split(",", 1)[1]
        image_binary = base64.b64decode(base64_data)
        mimetype = content.mime_type or "image/png"
        extension = guess_extension(mimetype) or ".png"
        tool_file = tool_file_manager.create_file_by_raw(..., file_binary=image_binary, mimetype=mimetype,
                                                         filename=f"generated_image{extension}")
except Exception:
    _logger.exception("Failed to save image file")
    return None

# Create MessageFile record.
# Use an independent session so this side-effect write does not
# commit or close the caller's request-scoped session.
message_file = MessageFile(...)
session.add(message_file)
session.flush()
return message_file.id

# caller:
with session_factory.create_session() as session:      # fresh session per image
    message_file_id = self._handle_multimodal_image_content(session=session, ...)
    session.commit()                                    # COMMIT before publish
if message_file_id:
    queue_manager.publish(QueueMessageFileEvent(message_file_id=message_file_id), ...)
```

**Flow:** chunk carries image content → require id/user/tenant (else warn-and-skip) → download-or-decode into a tool file → INSERT MessageFile on a dedicated session → commit → only then publish the event so the client never receives an id that 404s. Any storage failure logs and continues the stream (image lost, chat intact).
**Invariant:** Publish strictly AFTER durable commit — event-before-commit produces dangling references under load; the side-channel uses its own session because the streaming consumer has no reliable outer transaction; failures are fail-open by design (log, return None, stream continues).
**Probe:** `grep -c 'session.commit()' core/app/apps/base_app_runner.py` → 1; direct tests `tests/unit_tests/core/app/apps/test_base_app_runner.py::test_handle_invoke_result_stream_commits_message_file_before_publish` and `::test_handle_invoke_result_stream_agent_mode_handles_multimodal_errors`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_handle_invoke_result stream multimodal image message file", limit: 10 });
```

## Verdict
Adopt commit-then-publish with an isolated session for stream side-effects. Adapt the file store behind ToolFileManager. Omit data-URL handling if your providers never emit it.
