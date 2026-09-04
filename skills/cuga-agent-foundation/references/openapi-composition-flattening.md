<!-- capsule-v2 -->
# OpenAPI composition flattening — how do you turn $ref / 3.1 type-arrays / anyOf-allOf into one flat parameter schema an LLM can fill?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What are the reduction rules that collapse OpenAPI composition keywords into a single flat Schema without losing nullability or descriptions?

## Ref-carry-through, union→nullable+primary, single-variant unwrap, shallow merge
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/openapi_parser.py:193-277` (`SimpleOpenAPIParser._parse_schema`, `_resolve_ref` at :146-154).
**Signature:** `_parse_schema(self, schema_data) -> Optional[Schema]`; `_resolve_ref(self, ref: str) -> dict`.
**Data Shape:** Flat `Schema(type, format, description, default, enum, properties, items, required, ref, nullable, title)`; YAML specs are normalized via safe_load→json.dumps→from_json so there is ONE parse path.

### Decisive source
```python
# openapi_parser.py:216-222 — $ref does NOT discard the referencing site's metadata
if "$ref" in schema_data:
    resolved = self._resolve_ref(schema_data["$ref"])
    parsed = self._parse_schema(resolved)
    # carry through local description/title, if present
    if "description" in schema_data and parsed:
        parsed.description = schema_data["description"]
    if "title" in schema_data and parsed:
        parsed.title = schema_data["title"]
    return parsed
# :225-230 — OpenAPI 3.1 union types
if isinstance(raw_type, list):          # "type": ["string","null"]
    nullable = nullable or ("null" in raw_type)
    raw_type = next((t for t in raw_type if t != "null"), "") or ""
```
Composition ladder: `anyOf`/`oneOf` with exactly ONE non-null variant ⇒ parse that variant and OR-in nullability (`[$ref, null]` / `[primitive, null]` — the dominant real-world shape); otherwise ALL composition keys fall through to a SHALLOW MERGE with first-concrete-wins semantics per field (type/format, items, enum, description, title), properties dict-merged, required list UNIONED, and `type="object"` defaulted when merged properties exist but no type emerged. `_resolve_ref` navigates `#/`-stripped JSON-pointer segments and raises ValueError on non-dict hops or dead ends — malformed refs fail loudly instead of producing empty schemas.

**Flow:** endpoint parameters/requestBody/responses each route their `schema` through `_parse_schema` → ref resolution (with metadata carry-through) → 3.1 array-type normalization → composition reduction → plain-field extraction with recursive properties/items.
**Invariant:** Nullability must survive every reduction (array-form, sibling `nullable`, and null variants inside composition all OR together); a `$ref` never erases site-local description/title because those are what the LLM sees as parameter docs; unresolvable refs raise rather than silently flatten to empty.

**Probe:** No dedicated unit test in tests/unit for the parser — coverage caveat: exercised indirectly via mcp_manager registration flows; the reduction rules above are the contract, read source when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_parse_schema resolve_ref anyOf allOf nullable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four reduction rules in order (ref+carry-through, type-array, single-variant unwrap, shallow first-wins merge). Adapt the target Schema model to your tool registry. Omit allOf merging if your specs never use it — but keep the loud ref failure either way.
