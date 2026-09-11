<!-- capsule-v2 -->
# Form Field Primitive Registry — how does a Pydantic model become a channel-agnostic form definition?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you design form field primitives so one definition renders on dashboard, Slack, and email — and degrades where a widget can't exist?

## kind-discriminated base + per-category modules + option normalization
**Path/Symbol:** `forms/base.py` — `FormFieldBase` (:25–40); `forms/fields/{text,numeric,selection,media,date_time}.py` (~15 primitives); `selection._normalize_options` (:156–173); consumers `extract.py`, `slack/coerce.py`.
**Signature:** `FormFieldBase(BaseModel)`: `{name: str = "", kind: str, label/hint: str | None, required: bool = True}` + `ConfigDict(populate_by_name=True)`; DSL helpers return instances (`short_text(...) -> ShortText`).
**Data Shape:** every primitive carries a `kind: Literal[...]` discriminator; display-only kinds (DisplayText/Image/Video/PdfViewer/HtmlBlock) set `required=False`; values travel as ISO 8601 strings for dates ("JSON-safe across languages"); options accept `SelectOption | tuple[str,str] | str` (bare string ⇒ value=label).

### Decisive source
```python
class ShortText(FormFieldBase):
    kind: Literal["short_text"] = "short_text"
    subtype: ShortTextSubtype = "plain"   # plain|email|url|phone|currency|number|password
    ...
# Bare numeric inputs are ShortText with subtype="number"/"currency";
# Slider/rating/scale live in fields/numeric.py  (cross-module docstring pin)

def _normalize_options(raw):
    """Accept SelectOption, (value, label) tuples, or bare strings (value=label)."""
    elif isinstance(item, tuple):
        out.append(SelectOption(value=item[0], label=item[1]))
```

**Flow:** developer annotates a response Pydantic model (`Annotated[bool, switch(label=...)]`) → `extract_form()` fills name+required from the Pydantic field → definition ships to every channel → Slack coerces back via `_extract_value` isinstance dispatch; dashboard-native widgets degrade to link-out for Signature/RichText/Ranking.
**Invariant:** numeric AMOUNTS are text subtypes, NOT a NumericField class (docstring-pinned taxonomy decision); layout/display elements carry no `name` so coercion skips them; option normalization is the single entry point (numeric.Ranking imports it from selection).
**Probe:** `packages/python/tests/forms/test_primitives.py:131 test_options_accept_tuples_and_strings`; TS mirror behavior pinned in `packages/typescript-sdk/tests/forms.test.ts` (:17 Switch-from-boolean, :62 short_text, :67 long-text heuristic, :74 enum→single_select, :107 unsupported-primitive skip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "FormFieldBase SelectOption _normalize_options ShortText", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the discriminated-kind base, per-category module split, option-normalization ladder, and the display-kinds-set-required-False convention. Adapt your primitive list; keep amounts-as-text-subtypes unless you need locale parsing. Omit channel degradation matrix only if single-channel.
