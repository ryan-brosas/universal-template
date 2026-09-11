<!-- capsule-v2 -->
# F fluent builder — how do you offer `F.age >= 18` ergonomics when Python's comparison dunder contract fights you?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** how does the fluent field-reference builder produce Condition objects from operator syntax, and which Python object-model traps must a porter re-implement?

## FieldRef + singleton builder
**Path/Symbol:** `packages/graphrag-vectors/graphrag_vectors/filtering.py` (`FieldRef` :277-335, `_FieldBuilder.__getattr__` :347-349, singleton `F = _FieldBuilder()` :353).
**Signature:** `FieldRef(name).__eq__/__ne__/__gt__/__ge__/__lt__/__le__(other) -> Condition` plus methods `.contains/.startswith/.endswith/.in_/.not_in/.exists(value=True)`.
**Data Shape:** every dunder returns a fresh immutable-ish pydantic `Condition`; the builder itself holds no state, so `F` is import-safe as a module singleton.

### Decisive source
```python
# filtering.py:289-291 — type: ignore[override] is LOAD-BEARING:
# __eq__ must return Condition, breaking the hashability/identity
# contract Python expects for == on plain objects
def __eq__(self, other: object) -> Condition:  # type: ignore[override]
    return Condition(field=self.name, operator=Operator.eq, value=other)
```
```python
# filtering.py:347-349 — ANY attribute becomes a field name; typos are
# silently valid fields that evaluate False at runtime
class _FieldBuilder:
    def __getattr__(self, name: str) -> FieldRef:
        return FieldRef(name)
```

**Flow:** `F.status` → `__getattr__` wraps the NAME in a FieldRef → `F.status == "active"` → dunder returns `Condition(field="status", operator=eq, value="active")` → combinable with `&`/`|`/`~` (Condition defines them too). Non-dunder operators (contains/in_/exists) are explicit METHODS because Python has no operator syntax for them.
**Invariant:** dunder overloads must be defined on FieldRef for comparisons AND mirrored as `__and__/__or__/__invert__` on all four expression nodes — if a porter adds a fifth node type without the three combinators, `(a & b) | c` silently falls back to identity-based equality and produces wrong trees. `__hash__` is implicitly None once `__eq__` is overridden; these objects are not dict-key safe.
**Probe:** `tests/unit/vector_stores/test_filtering.py` TestFBuilder (:133-173) asserts `F.color == "red"` yields `isinstance(expr, Condition)` with exact field/operator/value; TestOperatorOverloads (:179-205) pins nesting shapes. 34 passed @pin via `$VENV_ROOT/grag-lane-venv/bin/python -m pytest tests/unit/vector_stores/test_filtering.py -q`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "FieldRef fluent builder condition operator overload", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the attribute-any-name builder + dunder-to-Condition mapping and the method-only set (contains/in_/exists); adapt naming to host DSL; omit the pydantic base if your conditions never serialize to LLM JSON (but then keep the round-trip tests as design rationale). No coverage caveat.
