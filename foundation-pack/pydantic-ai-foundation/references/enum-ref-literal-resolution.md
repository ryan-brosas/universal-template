<!-- capsule-v2 -->
# Terminal enum $ref → Literal — why does a bare class name for an enum schema corrupt generated signatures?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a JSON-Schema `$ref` target is a terminal enum def, how must the type-expression builder resolve it?

## enum-ref-literal-resolution
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/function_signature.py::_schema_to_type_expr` $ref branch (:608–613).
**Signature:** `elif 'enum' in ref_schema and ref_schema.keys().isdisjoint(('$ref', 'allOf', 'anyOf', 'oneOf')): return _schema_to_type_expr(ref_schema, defs, referenced_types, tool_name, path)`.
**Data Shape:** `$defs` entries emitted by Pydantic for enum classes are NON-object defs (just `{enum: [...]}` + optional title); object-shaped refs take the `_build_and_register_type` path instead.

### Decisive source
```python
ref_schema = _normalize_schema_node(defs[ref_name])
if ref_schema.get('type') == 'object' and 'properties' in ref_schema:
    _build_and_register_type(ref_name, ref_schema, defs, referenced_types, tool_name, path)
elif 'enum' in ref_schema and ref_schema.keys().isdisjoint(('$ref', 'allOf', 'anyOf', 'oneOf')):
    # Pydantic emits enum classes as non-object defs. Resolve terminal enum defs
    # inline as `Literal[...]`; a bare class name would never be defined.
    return _schema_to_type_expr(ref_schema, defs, referenced_types, tool_name, path)
```

**Flow:** tool signature carries an enum-typed param → schema has `$ref: '#/$defs/Color'` → resolver looks up the def → NOT object/properties → enum membership + no composition keys → recurse so the enum renders as `Literal['red','green','blue']` inline → provider receives self-contained types.
**Invariant:** three rules:
1. The composition-key disjointness check (`$ref/allOf/anyOf/oneOf` absent) is what makes the def TERMINAL — an enum wrapped in any combinator must not shortcut to Literal.
2. Emitting the bare ref name as a Python identifier produces code referencing an undefined name ("a bare class name would never be defined") — inline resolution isn't cosmetic, it's the difference between valid and broken generated signatures.
3. Order matters in the branch chain: object-with-properties first (named model types), terminal-enum second (inline), fall-through returns registered TypeSignature otherwise.
**Probe:** `tests/test_function_signature.py` (grep hits for `_schema_to_type_expr`/enum-Literal cases pin the rendering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_schema_to_type_expr ref_schema enum Literal function_signature", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt terminal-def inline resolution with explicit terminality tests in any $ref-resolving type renderer; adapt to your schema dialect; omit where your generator registers named enums.
