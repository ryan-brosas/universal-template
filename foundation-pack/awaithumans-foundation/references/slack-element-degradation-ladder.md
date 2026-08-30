<!-- capsule-v2 -->
# Slack Element Degradation Ladder — per-kind × cardinality element selection, form-derived addressing, and client-side truncation that fails loud

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you map rich form primitives onto a fixed palette of native elements — and how do submitted values get addressed back to the right field?

## Connected graph-selected seam
**Path/Symbol:** `channels/slack/blocks/selection.py` whole (:1-100) + `blocks/helpers.py` whole (:1-58, incl. `UnrenderableInSlackError` :14-19, `truncate` :29-31, `option` :34-39, `input_block` :42-58); round-trip twin `channels/slack/coerce.py::slack_values_to_response` (:36-52).
**Signature:** `single_select_element(field: SingleSelect)` / `multi_select_element(field: MultiSelect)` / `picture_choice_element(field: PictureChoice)` / `input_block(field, element) -> dict`.
**Data Shape:** thresholds `_SINGLE_RADIO_THRESHOLD = 4` / `_MULTI_CHECKBOX_THRESHOLD = 10` (:28-29); cap constants `SLACK_SELECT_MAX_OPTIONS=100`, header 150, plain text 3000, context value 200 (`utils/constants.py` :130-133); option labels cap 75.

### Decisive source
```python
def single_select_element(field: SingleSelect) -> dict[str, Any]:
    options = [option(o.value, o.label) for o in field.options[:SLACK_SELECT_MAX_OPTIONS]]
    if len(options) <= _SINGLE_RADIO_THRESHOLD:
        elem: dict[str, Any] = {"type": "radio_buttons", "action_id": field.name, ...}
    else:
        elem = {"type": "static_select", "action_id": field.name, ...}
```
The keystone — BOTH directions derive keys from the FORM DEFINITION. Write side (`helpers.input_block` :51):
```python
"block_id": f"{SLACK_BLOCK_ID_PREFIX}{field.name}",
```
Parse side (`coerce.py` :48-49):
```python
block_id = f"{SLACK_BLOCK_ID_PREFIX}{field.name}"
action = values.get(block_id, {}).get(field.name, {})
```
Loud unrenderable backstop (`surfaces._field_to_blocks` :403-405):
```python
raise UnrenderableInSlackError(
    f"Primitive '{field.kind}' has no native Slack renderer. "
    "Check form_renders_in(form, 'slack') before calling form_to_modal()."
)
```

**Flow:** every named input primitive → its category renderer → wrapped by `input_block` (label/required/hint + prefixed block_id). Selection ladder: single ≤4 → radio_buttons else static_select; multi ≤10 → checkboxes else multi_static_select; picture_choice ALWAYS degrades to selects ("Slack elements don't support images in options"); switch renders as two-option radio with default → initial_option; short-text subtypes pick typed elements (email_text_input / number_input + is_decimal_allowed). On submission the handler rebuilds the SAME `f"{prefix}{name}"` key to look up `(block_id, action_id)` inside Slack's opaque `state.values` bag.
**Invariant:** Slack's state structure is NEVER parsed structurally — only addressed by server-derived keys, so Slack shape changes can't silently misroute answers. Truncation is CLIENT-SIDE and deliberate ("fail loud rather than have Slack silently drop blocks"): truncate() ellipsizes at max_len−1+"…". Primitives with no native renderer fail LOUD at build time naming the capability predicate as the pre-check; Signature/Ranking are pinned unrenderable by tests. The error class lives in helpers.py specifically so catch sites don't import the full renderer set.

**Probe:** `tests/slack/test_blocks.py` — threshold twins `test_single_select_under_4_options_uses_radio_buttons` (:132-137) vs `..._over_4_options_uses_static_select` (:140-145), multi twins (:148-161), picture-choice fallback pair (:164-191), unrenderables `test_signature_raises_unrenderable`/:239-247 + `test_ranking_raises_unrenderable`/:250-258; switch default initial_option :112-114; typed subtypes :117-124.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "input_block truncate option element radio buttons checkboxes threshold unrenderable", limit: 8 });
```
Live at pin: radio test −30.05 (:105-109); under-4 test −28.39 (:132-137); `input_block` −22.69 (:42-58); `truncate` −22.19 (:29-31); `option` −19.2 (:34-39); selection quartet −19.18..−18.97; `UnrenderableInSlackError` −12.14 (:14-19).

## Verdict
Adopt the degradation ladder as a pure function of kind × cardinality, form-derived addressing on both write and parse sides, client-side truncation with loud caps, and an exception whose message names the pre-check predicate. Adapt thresholds to your element budget. Omit the dedicated error class only if your language makes cross-module exception imports free.
