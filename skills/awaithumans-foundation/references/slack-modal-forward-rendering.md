<!-- capsule-v2 -->
# Slack Modal Forward Rendering — build the Block Kit modal FROM the form definition and ride task identity in private_metadata

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you turn a JSON form definition into a Slack modal, and how does the submission handler know which task it belongs to without trusting Slack?

## Connected graph-selected seam
**Path/Symbol:** `packages/python/awaithumans/server/channels/slack/blocks/surfaces.py` — `form_to_modal` (:66-122), `task_metadata_blocks` (:140-167), dispatcher `_field_to_blocks` (:341-406); consumer `_handle_view_submission` in `routes/slack/interactions.py` (:556-627).
**Signature:** `form_to_modal(*, form: FormDefinition, task_id: str, task_title: str, task_payload: dict | None, redact_payload: bool = False, task_metadata: dict[str,str] | None = None) -> dict` (a Slack view payload).
**Data Shape:** modal `{type:"modal", callback_id: SLACK_MODAL_CALLBACK_ID ("awaithumans.review_modal"), title/submit/close plain_text, private_metadata: task_id, blocks:[...]}`; header → metadata context block → optional payload preview → one input block per field.

### Decisive source
```python
    if task_payload and not redact_payload:
        lines = [
            f"*{k}*: {truncate(str(v), SLACK_CONTEXT_VALUE_MAX)}" for k, v in task_payload.items()
        ]
        ...
    for field in form.fields:
        blocks.extend(_field_to_blocks(field))

    return {
        "type": "modal",
        "callback_id": SLACK_MODAL_CALLBACK_ID,
        ...
        "private_metadata": task_id,
        "blocks": blocks,
    }
```
Consumer side — identity out-of-band, authorize BEFORE coercion (:577-593):
```python
    # Authorise the submitter. Without this, anyone with a workspace
    # session who could trigger the modal (or replay a captured
    # `private_metadata` task_id) could complete tasks they were never
    # assigned to. ...
    authorised, why_not = await _slack_user_can_act_on_task(...)
    if not authorised:
        return {
            "response_action": "errors",
            "errors": {"awaithumans:_auth": why_not},
        }
```

**Flow:** claim/open action → `_open_modal_for_task` → `form_to_modal` → `views_open`. Submission → `_handle_view_submission`: 400 when private_metadata missing (:562-563) → fetch task → authorize submitter against the task (assignee-or-operator via directory mapping) → resolve completer from DIRECTORY ROW not @handle (:595-605) → `slack_values_to_response(form, state)` coercion → complete_task → fire-and-forget `update_slack_messages_for_task` because Slack expects the view_submission response within 3s (:619-624).
**Invariant:** nothing structural is trusted from Slack's blob — task identity rides OUTSIDE the state bag in `private_metadata`, and a captured task_id is useless without passing authorization. Redaction reaches display: `redact_payload=True` skips the payload-preview section entirely (`if task_payload and not redact_payload` :99), pinned by test. task_metadata renders as ONE context block between header and payload; ≤5 entries (`_METADATA_MAX_ENTRIES`), values truncated to 80 chars, `_+N more_` overflow marker, insertion order deliberately preserved.

**Probe:** `tests/slack/test_blocks.py` — `test_modal_has_required_top_level_fields` (:57-63, callback_id + private_metadata=="task-123"), `test_modal_prepends_title_header_and_payload_context` (:66-74), `test_redact_payload_hides_values` (:77-89). `tests/tasks/test_task_metadata.py::test_form_to_modal_includes_metadata_block` (:169-182, header→context→inputs ordering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "form_to_modal modal build form definition blocks private_metadata view submission", limit: 5 });
```
Live at pin: rank-1 `form_to_modal` −41.03 (:66-122); `test_form_to_modal_includes_metadata_block` −33.9 (:169-182); `_handle_view_submission` −31.2 (:556-627); `_open_modal_for_task` −19.39 (:313-352).

## Verdict
Adopt definition-driven modal assembly with identity in private_metadata and authorize-before-coercion on submission; adopt the 3s-budget fire-and-forget surface swap for anything slow after ack. Adapt block vocabulary to your platform SDK. Omit the inline `errors` rejection shape only if your channel supports redirect-based error surfaces instead.
