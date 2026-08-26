<!-- capsule-v2 -->
# rust-prompt-template-funnel — how do templates shape every LLM prompt in the summary pipeline?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What are the three prompt builders, their shared English directive injection points, and the template methods they consume?

## Three-stage prompt ladder over one Template object
**Path/Symbol:** `frontend/src-tauri/src/summary/processor.rs:build_chunk_summary_user_prompt` (:137-141), `build_combine_summary_user_prompt` (:143-147), `build_final_report_system_prompt` (:149-172); `Template::to_markdown_structure/to_section_instructions` (summary/templates/).
**Signature:** `fn build_final_report_system_prompt(section_instructions: &str, clean_template_markdown: &str) -> String`.
**Data Shape:** Stage 1 (per chunk): user prompt = English directive + "concise but comprehensive" ask + `<transcript_chunk>` wrapper. Stage 2 (combine): chunk summaries joined `"\\n---\\n"` inside `<summaries>`. Stage 3 (final): SYSTEM prompt carries numbered rules ("Only use information present…", section fallback string `"None noted in this section."`, output-only-markdown) + SECTION-SPECIFIC INSTRUCTIONS + `<template>` block; USER prompt wraps content in `<transcript_chunks>` and appends `<user_context>` ONLY when custom_prompt non-empty. All four prompts embed `ENGLISH_BASE_SUMMARY_INSTRUCTION` — pinned by tests asserting its presence AND length ≤ 120 chars.

### Decisive source
```rust
let clean_template_markdown = template.to_markdown_structure();
let section_instructions = template.to_section_instructions();
let final_system_prompt = build_final_report_system_prompt(&section_instructions, &clean_template_markdown);
```

**Flow:** template_id resolved once in service (`templates::get_template`, failure ⇒ process failed) → both template renderings fingerprinted for cache invalidation (`template_cache_fingerprint` = FNV over structure + "\\n---SECTION-INSTRUCTIONS---\\n" + instructions) → consumed by stage-3 system prompt.
**Invariant:** The XML-ish tag wrappers (`<transcript_chunk>/<summaries>/<transcript_chunks>/<user_context>`) double as instruction-isolation markers — rule 3 of the final prompt explicitly says to ignore instructions inside `<transcript_chunks>` (prompt-injection defense for transcript text).
**Probe:** battery T05 pins ENGLISH_BASE_SUMMARY_INSTRUCTION == 9 occurrences incl. tests; T15 pins `SECTION-INSTRUCTIONS` == 1 in service.rs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "build_final_report_system_prompt to_section_instructions template", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-stage funnel + tag-wrapped payload isolation + fingerprinted template rendering; adapt template content; omit built-in template prose. Direct tests assert directive presence across all builders.
