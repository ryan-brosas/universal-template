<!-- capsule-v2 -->
# Slack View-State Coercion — how does a nested Block Kit submission become a flat typed response?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you convert Slack's block_id→action_id `state.values` tree into the developer's response schema without losing blank-vs-missing distinctions?

## Form-definition-driven dispatch over prefixed block ids
**Path/Symbol:** `packages/python/awaithumans/server/channels/slack/coerce.py` — `slack_values_to_response` (:36–52), `_extract_value` (:55–125), `_parse_number` (:128–135).
**Signature:** `slack_values_to_response(form: FormDefinition, view_state: dict) -> dict[str, Any]`; `_extract_value(field, action: dict) -> Any`; `_parse_number(raw, *, decimal: bool) -> float | int | None`.
**Data Shape:** lookup key = `values[{SLACK_BLOCK_ID_PREFIX}{field.name}][{field.name}]` (prefix `"awaithumans:"` from constants — deterministic field-name extraction); per-type action blobs: `selected_option` / `selected_options` / `value` / `selected_date` / `selected_date_time` / `selected_time` / `files`.

### Decisive source
```python
for field in form.fields:
    if not field.name:
        continue  # layout/display element — no response value
    block_id = f"{SLACK_BLOCK_ID_PREFIX}{field.name}"
    action = values.get(block_id, {}).get(field.name, {})
    response[field.name] = _extract_value(field, action)
...
if isinstance(field, Switch):
    opt = action.get("selected_option")
    return None if opt is None else opt.get("value") == "true"
if isinstance(field, PictureChoice):
    if field.multiple:
        return [o["value"] for o in action.get("selected_options", []) ...]
    opt = action.get("selected_option")
    return [opt["value"]] if opt and "value" in opt else []
```

**Flow:** iterate the FORM definition (source of truth), not the Slack payload → skip nameless layout/display fields → per-primitive isinstance dispatch → blank fields become None (Switch), [] (PictureChoice/MultiSelect), or None (texts/numbers via `_parse_number`) → server response-validation layer catches missing requireds.
**Invariant:** coercion is driven by what the form EXPECTED, never by walking the payload; PictureChoice single-select still returns a LIST (`[opt["value"]]`) so the response shape is multiple-independent; number subtypes coerce float→int when `decimal=False`; unknown field kinds silently coerce to None ("the form shouldn't have been rendered in Slack").
**Probe:** `packages/python/tests/slack/test_coerce.py` (:35/:49/:63 switch true/false/blank-none, :79 currency→float, :94 single select, :108 multi checkboxes, :125 picture-single-returns-list, :146 date picker, :155 slider float, :161 star int, :189 layout-fields skipped, :212 missing-block-yields-none).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "slack_values_to_response _extract_value SLACK_BLOCK_ID_PREFIX", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt form-driven iteration + prefixed block-id scheme + per-primitive blank-value table. Adapt the primitive set to your field taxonomy. Omit nothing else — every branch above has a pinned test.
