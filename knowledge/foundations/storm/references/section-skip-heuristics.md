<!-- capsule-v2 -->
# Section-skip heuristics — which outline sections must never get their own LLM call?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How does the article generator decide which first-level sections to write, and what replaces the skipped ones?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/storm_wiki/modules/article_generation.py:StormArticleGenerationModule.generate_article` (:53-133) + polish twin `PolishPageModule.forward` (article_polish.py:87-102).
**Signature:** `generate_article(topic, information_table, article_with_outline, callback_handler=None) -> StormArticle`.
**Data Shape:** Sections dispatched by lowercase/startswith predicates over `get_first_level_section_names()`; results collected as dicts `{section_name, section_content, collected_info}`.

### Decisive source
```python
for section_title in sections_to_write:
    if section_title.lower().strip() == "introduction":
        continue                      # never a standalone intro section
    if section_title.lower().strip().startswith("conclusion") or \
       section_title.lower().strip().startswith("summary"):
        continue                      # conclusion/summary* handled elsewhere
    ...executor.submit(self.generate_section, ...)
# empty-outline fallback: write ONE section named after the topic, query = topic
if len(sections_to_write) == 0:
    logging.error(f"No outline for {topic}. Will directly search with the topic.")
# polish side: lead section written from the FULL draft, then prepended as "# summary"
lead_section = f"# summary\n{polish_result.lead_section}"
polished = "\n\n".join([lead_section, polish_result.page])
```

**Flow:** First-level sections fan out to threads (introduction/conclusion*/summary* excluded) → each writes against top-k retrieved evidence → sections merge back through `update_section` → polish generates the LEAD via `WriteLeadSection` (≤4 paragraphs, sourced) and optionally dedupes the whole page via a second LM (`remove_duplicate` flag), stripping any leaked `"The lead section:"` prefix (:93-94).
**Invariant:** (1) The summary-shaped HOLE in generation is deliberate — the lead is written LAST from the finished draft, then inserted at FRONT (`insert_to_front=True` for root "summary" in insert_or_create_section). (2) `show_guidelines=False` is set in polish contexts for cross-family LM robustness — keep it when porting to non-OpenAI engines. (3) Section futures are consumed via `as_completed`, so merge order is nondeterministic; reference renumbering afterwards restores reading order. (4) `article_gen_lm` (not polish_lm) writes the lead.
**Probe:** deterministic pin GREEN — article_generation.py:96-103 skip predicates byte-read this pass; graph resolves module line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "generate_section introduction conclusion skip thread", limit: 10 });
```

## Verdict
Adopt skip-intro/write-body/lead-last for Wikipedia-style generation; adapt the banned-section vocabulary; omit the whole-page LM dedupe pass if your budget is tight (flag-gated upstream). Caveat: no upstream tests; source-pinned.
