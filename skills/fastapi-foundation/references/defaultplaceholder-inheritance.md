<!-- capsule-v2 -->
# DefaultPlaceholder inheritance — How do router/app defaults flow to routes without erasing explicit user values?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** How does FastAPI distinguish "user passed X" from "X is the default" when composing app → router → route configuration?

## Sentinel-wrapped defaults + get_value_or_default
**Path/Symbol:** `fastapi/datastructures.py:DefaultPlaceholder/Default/_Unset` (153–187) + `fastapi/utils.py:get_value_or_default` (121–136); consumed in `_RouterIncludeContext.for_include` (1329–1339), `combine` (1351–1364), `add_api_route` (`get_value_or_default(response_class, self.default_response_class)`), and `_populate_api_route_state` (response_model `Default(None)`, generate_unique_id_function `Default(generate_unique_id)`).
**Signature:** `Default(value: DefaultType) -> DefaultType` (returns a placeholder typed as the value); `get_value_or_default(first_item, *extra_items)` returns the first NON-placeholder, else the first item.
**Data Shape:** placeholder equality compares inner values (`isinstance(o, DefaultPlaceholder) and o.value == self.value`), so two `Default(JSONResponse)` compare equal but are still distinguishable from a bare class.

### Decisive source
```python
class DefaultPlaceholder:
    def __init__(self, value: Any): self.value = value
    def __bool__(self) -> bool: return bool(self.value)
    def __eq__(self, o: object) -> bool:
        return isinstance(o, DefaultPlaceholder) and o.value == self.value

def get_value_or_default(first_item, *extra_items):
    """Pass items or `DefaultPlaceholder`s by descending priority.
    The first one to _not_ be a `DefaultPlaceholder` will be returned.
    Otherwise, the first item (a `DefaultPlaceholder`) will be returned."""
```

**Flow:** every inheritable option travels as either an explicit value or `Default(inner)` → at each composition layer (app→router include, router→route add), `get_value_or_default(explicit, parent_default)` picks the nearest EXPLICIT setting while preserving a placeholder if everything is default → consumers unwrap via `value.value` when `isinstance(x, DefaultPlaceholder)` (e.g. `actual_response_class`, `use_dump_json` gating, unique-id generation).
**Invariant:** (1) Truthiness can't leak through — `__bool__` forwards to the wrapped value, so `if response_class:` behaves naturally while `isinstance` checks preserve provenance. (2) `response_model=Default(None)` is load-bearing: it distinguishes "no response_model given" (derive from return annotation / stream item type) from an explicit `response_model=None` (never derive). (3) The pattern is why overriding a default on the APP propagates to routes that never mentioned it, yet a route-level explicit value always wins.
**Probe:** `tests/test_default_response_class.py` + `tests/test_default_response_class_router.py` pin exactly this propagation; `tests/test_response_model_as_return_annotation.py` pins the Default(None) derivation gate.
