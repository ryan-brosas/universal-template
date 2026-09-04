<!-- capsule-v2 -->
# Function-signature rendering with structural type dedup

## Source / Question
`pydantic_ai_slim/pydantic_ai/function_signature.py` — How does pydantic-ai render tool definitions as human-readable Python function signatures for LLMs, and how does it dedup structurally-identical TypedDict types while prefixing genuinely-conflicting names? A porter must get the conflict-resolution and keyword-only rendering right.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/function_signature.py` — `FunctionSignature` (240–~700), `render` (249–277), `_render` (279–318), `from_schema` (320–368), `get_conflicting_type_names` (370–404), `collect_unique_referenced_types` (406–416), `render_type_definitions` (418–~470), `TypeSignature.structurally_equal` (193–203), `_replace_type_refs` (820–~846), `_type_name_overrides` ContextVar (31).

## Signature
```python
class FunctionSignature:
    def render(self, body, *, name=None, description=None, is_async=None, conflicting_type_names=frozenset()) -> str
    @classmethod
    def from_schema(cls, *, name, parameters_schema, return_schema=None) -> FunctionSignature
    @staticmethod
    def get_conflicting_type_names(signatures: list[FunctionSignature]) -> frozenset[str]
```

## Data Shape
Type-expr tree: `SimpleTypeExpr`/`LiteralTypeExpr`/`GenericTypeExpr`/`UnionTypeExpr`; `TypeSignature` (TypedDict class defs) with `name`, `fields`, `structurally_equal`. `_type_name_overrides: ContextVar[dict[str,str]]` maps original type names → tool-prefixed names during render.

## Decisive source
`get_conflicting_type_names` (370–404): iterate every signature's `referenced_types`; first-seen name becomes the canonical instance; a later type with the SAME name and `structurally_equal` structure is replaced by the canonical (`_replace_type_refs` rewrites all refs in that signature's TypeExpr trees) and dropped; a later type with the same name but DIFFERENT structure is added to `prefixed` (needs a tool-name prefix). Returns the prefixed set. `render` (249–277) sets `_type_name_overrides = {n: f'{render_name}_{n}' for n in conflicting_type_names}` in a ContextVar, so `TypeSignature.display_name` resolves prefixed names at render time without mutating the shared type objects.

## Flow / Invariant
1. **Self-contained signatures**: each signature keeps all its referenced types (so it remains portable), but identical types (same name + structure) are unified to the SAME object instance.
2. **Structural equality** (`structurally_equal`, 193–203) is the dedup key — name alone is insufficient because two tools can define a `User` with different shapes.
3. **Prefix only on genuine conflict**: same name + different structure → tool-name prefix at render time (via ContextVar, not mutation); same name + same structure → unified canonical.
4. **Keyword-only params**: `_render` forces `*, ` before params so LLMs always use named arguments.
5. **Param/return $defs independence**: `from_schema` processes parameter and return schemas independently (each resolves `$ref`s against its own `$defs`); cross-signature collisions are deferred to `get_conflicting_type_names`.
6. **Dedup within a signature** merges structurally-identical param/return referenced types before cross-signature conflict detection.

## Probe (direct test)
`tests/test_function_signature.py` (1,594L): `test_get_conflicting_type_names_substring_names` (:54), `test_render_definition_with_conflicting_types` (:101), `test_dedup_identical_types_unified` (:166), `test_dedup_replaces_nested_generic_and_union_refs_with_canonical` (:206), `test_dedup_mixed_identical_and_conflicting_from_schemas` (:272), `test_structurally_equal` (:429), `test_tool_definition_function_signature_computed_from_schema` (:527).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'get_conflicting_type_names structurally_equal'` → `function_signature.TypeSignature.structurally_equal` (193–203), `FunctionSignature.get_conflicting_type_names` (371–404).

## Verdict
**Adopt** the structural-dedup + render-time-prefix pattern (ContextVar overrides, not mutation) — a clean way to present many tool schemas to an LLM without name collisions. **Adapt** the type-expr tree to your schema dialect.
