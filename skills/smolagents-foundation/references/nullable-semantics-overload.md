<!-- capsule-v2 -->
# Nullable-semantics overload — one schema flag means "has default", "accepts None", AND "may be omitted"

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory project `smolagents`. **Question:** What does `nullable: true` in a smolagents tool input actually guarantee — and which two behaviors does the project itself acknowledge as bugs?

## Path/Symbol
- Writers: `src/smolagents/_function_type_hints_utils.py:_convert_type_hints_to_json_schema` (:311-315 default⇒nullable; :398-400 None∈union⇒nullable).
- Reader: `src/smolagents/tools.py:validate_tool_arguments` (:1384 nullable⇒null accepted; :1400-1404 nullable⇒omittable).
- Consistency cross-check: `src/smolagents/tools.py:Tool.validate_arguments` (:216-225).

## Signature
`inputs[name]["nullable"]: bool` — single flag, three meanings.

## Data Shape
Flag written by TWO independent causes: (a) parameter has a default value, (b) `None` appears in the annotation union. Read as TWO independent permissions: null VALUE allowed, and key MAY BE MISSING.

### Decisive source
```python
# _function_type_hints_utils.py:311-315 — cause (a)
if param.default == inspect.Parameter.empty: required.append(param_name)
else: properties[param_name]["nullable"] = True
# :398-400 — cause (b)
if type(None) in args: return_dict["nullable"] = True
# tools.py:1400-1404 — reader treats it as omittable
if key not in arguments and not key_is_nullable:
    raise ValueError(f"Argument {key} is required")
```
```python
# tests/test_tools.py:990-999 — acknowledged conflation, test SKIPPED as TODO:
# "property is marked as nullable because it can be None, but it can't be missing because it is required"
pytest.param("required_supported_none", str | None, ..., ..., "Argument param is required",
    marks=pytest.mark.skip(reason="TODO: Fix this test case")),
# :1005-1014 — inverse conflation also skipped:
# "property is marked as nullable because it has a default value, but it can't be None"
pytest.param("optional_unsupported_none", str, "default", None,
    "Argument param has type 'null' but should be 'string'",
    marks=pytest.mark.skip(reason="TODO: Fix this test case")),
```

## Flow
Author writes `def f(x: str | None)` (required) or `def f(x: str = "d")` (no None) → both collapse to `{"type":"string","nullable":true}` → at call time BOTH are treated as optional-with-null-allowed. So a required-but-Optional param silently accepts omission (forward then receives nothing → TypeError inside forward), and a defaulted non-Optional param rejects explicit None with a confusing "type 'null' but should be 'string'". `Tool.validate_arguments` (:216-225) can only keep hand-authored `inputs` dicts CONSISTENT with forward hints (nullable present in one ⇒ must be in the other); it cannot disentangle the overloaded meaning.

## Invariant
Do not port nullable as if it were OpenAPI's `nullable` + `required` split — smolagents deliberately (if imperfectly) fuses optionality into one bit and documents the fallout in skipped tests. If your porter needs strict semantics, derive TWO flags at schema time (has_default, accepts_none) before the shape reaches validation.

## Probe
`tests/test_tools.py::test_validate_tool_arguments_nullable` (:973-1068): ACTIVE cases pin that `str|None` + None value passes, missing required raises, missing optional passes; the two SKIPPED cases are the honest record of the overload. Live probe: build `f(x: str | None)` with no default, call `validate_tool_arguments(tool, {})` → NO error even though forward would fail on missing x.

## Get live surrounding code
**Retrieve (executed 2026-08-26, project `smolagents`):**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "validate_tool_arguments nullable optional default required", limit: 10 });
// rank1-2: validate_tool_arguments :1361-1412, Tool.validate_arguments :144-226; tests #4/#7/#8: test_validate_tool_arguments :954-970 & :1035-1068
```

## Verdict
Adopt the awareness: any hint-derived schema builder that sets one flag from two causes will inherit this exact bug pair. Adapt by splitting the flags at generation time. Omit copying the skip-list; carry the lesson instead.
