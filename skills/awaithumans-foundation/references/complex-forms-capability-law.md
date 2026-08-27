<!-- capsule-v2 -->
# Complex Form Primitives & Capability Matrix — Table/Subform and the link-out law

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How are nested/tabular form fields modeled, and how does ONE capability table decide whole-form fallback per channel?

## kind-discriminated complex fields + recursive unsupported_fields walk
**Path/Symbol:** `packages/python/awaithumans/forms/fields/complex.py` — `TableColumnKind` Literal (:27-36), `TableColumn` (:39-51), `Table` (:57-66), `Subform` (:69-78), DSL helpers `table()`/`subform()` (:84-133); capability matrix `forms/capabilities.py` — `CAPABILITIES` dict (:34-70), `field_renders_in` (:73), `form_renders_in` (:78), `unsupported_fields` (:83-107).
**Signature:** value shapes: Table ⇒ `list[dict]` keyed by column NAME (homogeneous typed columns, variable rows); Subform ⇒ `list[dict]` keyed by FIELD name (repeated group of arbitrary fields, recursively nestable).
**Data Shape:** capabilities row per kind × {dashboard, slack, email_interactive, email_plain}; `table`/`subform` are LINK_OUT everywhere except dashboard (:68-69).

### Decisive source
```python
def form_renders_in(form, channel) -> bool:
    return not unsupported_fields(form, channel)
...
def unsupported_fields(form, channel) -> list[str]:
    def walk(fields):
        for f in fields:
            kind = getattr(f, "kind", None)
            if kind is None or kind not in CAPABILITIES:
                continue                      # layout/display elements skip
            if CAPABILITIES[kind][channel] == ChannelSupport.LINK_OUT:
                offenders.append(getattr(f, "name", None) or getattr(f, "label", None) or kind)
            if isinstance(f, SectionCollapse | Subform):
                walk(list(f.fields))          # recursion is the point
    walk(list(form.fields))
    return offenders
```
Docstring law: if ANY field forces link-out in a channel, the WHOLE form falls back in that channel — the typed-response contract survives regardless of which path the human took. Slack/email render complex fields as a "Complete in dashboard" link.

**Flow:** developer builds definition (DSL helpers normalize TableColumn dicts) → renderers consult CAPABILITIES before building output → native channels render; degraded channels emit link-out with offender names available for UI hints.
**Invariant:** the matrix is the SINGLE SOURCE OF TRUTH and must cover every primitive × channel (`test_capabilities_cover_every_primitive_and_channel`:58 asserts exact-set equality both axes) — adding a primitive without a row breaks the test, not production.
**Enforcement point:** the predicate is backed by a LOUD build-time backstop — `surfaces._field_to_blocks` (:341-406) ends in `raise UnrenderableInSlackError(f"Primitive '{field.kind}' has no native Slack renderer. Check form_renders_in(form, 'slack') before calling form_to_modal().")` (:403-405), i.e. bypassing the pre-check fails loud instead of rendering garbage; the card side mirrors it by OMITTING the Open-in-Slack button when `unsupported_fields` is non-empty (pinned by `test_blocks.py::test_open_review_message_with_unsupported_fields_omits_open_button` :277-287). Signature/Ranking are pinned unrenderable by tests :239-258.
**Probe:** `packages/python/tests/forms/test_capabilities.py` (`test_recursive_children_are_checked`:80, `test_section_collapse_children_checked`:92) + `tests/forms/test_primitives.py` roundtrip including table/subform (:95-118) and `test_recursive_subform`:174. Suites green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "Table Subform TableColumn table subform complex fields", limit: 5 });
```
Live rank-1..5 line-exact across complex.py; capability functions rank-1/2 on their own query.

## Verdict
Adopt the any-field-falls-back-whole-form rule and the exhaustive-capability test; extend column kinds/subform depth to your product; omit the Slack/email degradation arms only if you are dashboard-single-channel.
