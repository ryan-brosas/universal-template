<!-- capsule-v2 -->
# exec-tool-description-assembly — what text does the model see for `exec`, and which parts are conditional?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** When porting the code-action tool surface, which sections of the `exec` prompt are static vs derived, and when does each get appended?

## build_exec_tool_description section ladder
**Path/Symbol:** `codex-rs/code-mode-protocol/src/description.rs` : `build_exec_tool_description` (:261-340).
**Signature:** `fn build_exec_tool_description(enabled_tools: &[ToolDefinition], deferred_tools: &[ToolDefinition], namespace_descriptions: &BTreeMap<String, ToolNamespaceDescription>, default_exec_yield_time_ms: u64, code_mode_only: bool, image_detail_visibility: ImageDetailVisibility) -> String`.
**Data Shape:** enabled = tools exposed as callable globals; deferred = advertised-but-not-bound (discoverable via `ALL_TOOLS`); sections joined with `\n\n`.

### Decisive source
```rust
sections.push(EXEC_DESCRIPTION_TEMPLATE.replace(
    "Defaults to 10000 ms.",
    &format!("Defaults to {default_exec_yield_time_ms} ms."),
));
if image_detail_visibility == ImageDetailVisibility::Hidden {
    sections[0] = sections[0].replace(LEGACY_IMAGE_HELPER_DESCRIPTION, UNIFIED_IMAGE_HELPER_DESCRIPTION);
}
if !deferred_tools.is_empty() { sections.push(DEFERRED_NESTED_TOOLS_GUIDANCE.to_string()); }
if !code_mode_only { return sections.join("\n\n"); }   // non-code-mode-only: STOP here
let has_mcp_tools = enabled_tools.iter().chain(deferred_tools)
    .any(|tool| mcp_structured_content_schema(tool.output_schema.as_ref()).is_some());
if has_mcp_tools { sections.push(format!("Shared MCP Types:\n```ts\n{MCP_TYPESCRIPT_PREAMBLE}\n```")); }
```

**Flow:** (1) template with yield default substituted → (2) optional image-helper swap when detail hidden → (3) deferred-tools guidance if any deferred exist → (4) EARLY RETURN unless `code_mode_only` → (5) MCP TypeScript preamble once if ANY enabled-or-deferred output schema matches the CallToolResult shape → (6) per-tool headings grouped under namespace headers printed ONCE per namespace group (empty descriptions skip the header entirely).
**Invariant:** The MCP preamble is emitted at most once and only in `code_mode_only` mode — a porter who emits it unconditionally bloats every direct-tool prompt. Namespace guidance is deduped by tracking `current_namespace` across the sorted walk, never by set membership.
**Probe:** `codex-rs/code-mode-protocol/src/description.rs` tests `code_mode_only_description_groups_namespace_instructions_once` (`assert_eq!(description.matches("## mcp__sample").count(), 1)`), `code_mode_only_description_renders_shared_mcp_types_once`, and `exec_description_mentions_deferred_nested_tools_when_available`.

## MCP-shape detection is structural, not name-based
**Path/Symbol:** `description.rs` : `mcp_structured_content_schema` (:464-503).
**Data Shape:** `Option<&JsonValue>` — Some(structuredContent schema) iff output schema has `properties.content.type=="array"` with object items AND boolean `isError` AND object `_meta`.
**Invariant:** Detection keys on the four-field CallToolResult shape; a plain object output never triggers preamble emission. Missing `structuredContent` defaults to `true` (permissive unknown).

## Identifier normalization
**Path/Symbol:** `description.rs` : `normalize_code_mode_identifier` (:346-368).
**Data Shape:** first char must be `_`,`$`, or ascii alpha; subsequent chars additionally numeric; everything else becomes `_`; empty input → `"_"`. Dots/dashes in MCP names (`mcp__srv__tool`) survive because underscores are legal.
**Invariant:** The normalized global name IS the key the V8 runtime binds on the `tools` object (`globals.rs` uses `tool.global_name`) — prompt rendering and runtime binding share this one function; porting them separately desyncs call sites from bindings.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "build_exec_tool_description normalize_code_mode_identifier", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the section ladder, single-emission MCP preamble, structural shape detection, and shared normalizer. Adapt template wording to your harness. Omit the specific helper prose (image/audio/generatedImage descriptions are product copy). Direct tests exist in-file and pass at the pinned commit.
