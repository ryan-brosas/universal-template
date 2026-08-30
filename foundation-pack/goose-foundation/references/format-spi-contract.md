<!-- capsule-v2 -->
# Format SPI contract — what fixed function family must every provider payload module expose, and how are tool schemas and request params sanitized before they touch the wire?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** what is the minimal uniform surface a new format module must implement, and which sanitizer rules keep third-party validators accepting your tools?

## Shared mapper surface + schema sanitizer
**Path/Symbol:** `crates/goose-provider-types/src/formats.rs` (1-8, module fan-out); `crates/goose-provider-types/src/formats/openai.rs`:`format_tools` (660-680), `validate_tool_schemas` (947-957), `sanitize_schema_node` (969-1014), `normalize_nullable` (1022-1069), `sanitize_function_name` (1922-1929), `is_reserved_request_param_key` (62-64); `crates/goose-provider-types/src/formats/snowflake.rs` (whole file, 725 lines) as the degenerate member.
**Signature:** per module: `format_messages(…)->Vec<Value>`, `format_tools(&[Tool])->Result<Vec<Value>>`, `format_system(&str)->Value`, `response_to_message(&Value)->Result<Message>`, `response_to_streaming_message(stream)`, `create_request(…)->Result<Value>`; helpers `pub fn validate_tool_schemas(tools: &mut [Value])`, `pub fn sanitize_function_name(name: &str) -> String`.
**Data Shape:** Tools in as rmcp `Tool{name, description, input_schema}` → out as dialect JSON (`function.name/parameters`, anthropic `name/description/input_schema`, snowflake `{tool_spec:{type:"generic",…}}`). Request params merge skips goose-internal keys and reserved wire keys.

### Decisive source
```rust
// Moonshot's walle validator rejects oneOf behind a $ref as "infinite
// recursion" because its termination check only traverses anyOf. The two
// are interchangeable for tool-argument schemas, so emit the more widely
// supported form.
if !obj.contains_key("anyOf") {
    if let Some(one_of) = obj.remove("oneOf") { obj.insert("anyOf".to_string(), one_of); }
}
...
// normalize_nullable: schemars 1.x "type": ["integer","null"] -> "integer";
// anyOf:[T,{type:null}] unwraps to T merging sibling keys (description/default)
// — optional-ness already lives in `required`.
```
Sanitizer ladder: ensure top-level `"type":"object"`; recurse through properties/$defs/definitions/anyOf/allOf/prefixItems/items/additionalProperties; object nodes get default empty `properties{}`+`required[]`. Name rules: `sanitize_function_name` maps `[^a-zA-Z0-9_-]→_` then truncates to `MAX_FUNCTION_NAME_LENGTH = 128`; `is_valid_function_name` full-match check decides Err-vs-Ok on decode. Duplicate tool names: openai/databricks `format_tools` return `Err("Duplicate tool name")`; anthropic silently dedupes via HashSet (know your host's strictness). Snowflake shows the degenerate SPI member: text-only projection (thinking/images/tool REQUESTS dropped; tool results inlined as `"Tool result: …"` text), `tool_spec` wrapper objects, and a description-request heuristic that strips tools entirely when system contains "Reply with only a description in four words or less".

**Flow:** module fan-out (formats.rs declares submodules only) → provider client picks its module → format_messages/tools/system produce dialect JSON → validate_tool_schemas repairs schemas → create_request assembles payload filtering internal/reserved params.
**Invariant:** the SPI signature family is the porting interface — a new dialect implements the same seven functions; every tool spec leaving the process has an `anyOf`-only, non-null-typed, object-rooted schema with names matching `[a-zA-Z0-9_-]{1,128}`.
**Probe:** `cargo test -p goose-provider-types --lib formats::openai::test_validate_tool_schemas` plus suite pins `test_validate_tool_schemas_sanitizes_defs`, `test_sanitize_function_name`, `test_is_valid_function_name`, `test_format_tools_duplicate`, `test_request_params_preserve_reserved_fields`, and snowflake's own `test_create_request_excludes_tools_for_description` / `test_parse_streaming_response` (`cargo test -p goose-provider-types --lib snowflake`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "validate_tool_schemas sanitize_schema_node normalize_nullable oneOf anyOf", limit: 10, fields: ["lines"] });
```

## Verdict
Adopt the SPI shape, the schema-sanitizer ladder, and the name sanitation/truncation as one portable unit. Adapt duplicate-name policy and param-reserved lists per host strictness. Omit snowflake's content-dropping projection unless your target endpoint truly lacks tool/thinking/image support — it is documented here as the boundary case of the same interface, not as recommended behavior.
