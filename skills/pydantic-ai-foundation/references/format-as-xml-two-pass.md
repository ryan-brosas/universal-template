<!-- capsule-v2 -->
# format_as_xml — two-pass structure walk, 'once' field attributes, rootless rendering

## Source / Question
`pydantic_ai_slim/pydantic_ai/format_prompt.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you render arbitrary Python objects (dataclasses, BaseModel, mappings, iterables) as LLM-friendly XML with field metadata (title/description) shown once even when a field repeats across list items — and why does the walk run BEFORE serialization? A porter will serialize first (losing Field metadata) or re-emit attributes on every repeated element.

## Path / Symbol
`format_prompt.py` — `format_as_xml()` (:20–77), `_ToXml` dataclass (:80–224): `_to_xml` (:102–133), `_parse_data_structures` (:187–220), `_create_element` (:157–166), `_rootless_xml_elements` (:227–231).

## Signature
```python
def format_as_xml(obj: Any, *, root_tag: str | None = None, item_tag: str = 'item',
                  none_str: str = 'null', indent: str | None = '  ',
                  include_field_info: Literal['once'] | bool = False) -> str
```

## Data Shape
Supports scalars (str/bytes/bool/int/float/Decimal/date/time/timedelta/UUID/Enum), Mapping, Iterable, dataclass, BaseModel. Two collectors filled by a PRE-pass over the ORIGINAL object: `_fields_info` maps dotted paths → (Class.field repr, FieldInfo|ComputedFieldInfo) and `_element_names` maps paths → class names so untagged nested models/dataclasses get their class name as element tag. Only `title`/`description` field attributes are extracted.

### Decisive source — the two-pass split (:111–128 + :157–166)
```python
if is_dataclass(value) and not isinstance(value, type):
    self._init_structure_info()          # PRE-pass fills _fields_info/_element_names ONCE
    if tag is None:
        element.tag = value.__class__.__name__
    self._mapping_to_xml(element, asdict(value), path)
    return element
...
# _create_element: attribute emission keyed on path, gated for 'once'
if self.include_field_info and self.include_field_info != 'once' or field_repr not in self._included_fields:
    for k, v in self._extract_attributes(field_info).items():
        element.set(k, v)
    self._included_fields.add(field_repr)
```

**Flow:** pre-walk the raw object collecting per-path metadata (model_dump would destroy it) → main walk emits elements; BaseModel dumps via `model_dump(mode='json')` at emit time but reads metadata from the collector; `include_field_info='once'` adds title/description attributes only on the FIRST occurrence of each field path (`_included_fields` set); `root_tag=None` renders each top child as an independent string joined by newline (no wrapper element). Unsupported types raise TypeError loudly; int keys are str()'d, other non-str keys raise.

**Invariant:** Metadata collection must happen on the original object BEFORE any dump; the 'once' set keys on `ClassName.field_name` so repetition across sibling list items still collapses to one attribute emission. Path addressing (`a.b.[0].c`) must stay consistent between the two passes.

**Probe:** `tests/test_format_as_xml.py` — `test_fields` (:270, include_field_info matrix), `test_repeated_field_attributes` (:274, the once-semantics), `test_nested_data` (:400), `test_root_tag`/:160, `test_no_root`/:592, `test_invalid_value`/:603.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'format_as_xml _ToXml _parse_data_structures'
```

## Verdict
**Adopt** the two-pass design whenever prompt examples need schema hints inline. **Adopt** the once-attribute rule to keep prompts compact. **Adapt** the scalar ladder to your host's types. **Omit** the rootless join formatting if you always wrap prompts.
