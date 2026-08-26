<!-- capsule-v2 -->
# Wiki-TOC persona induction — how are writer personas induced from real Wikipedia structure without letting the ground-truth page leak in?

**Source:** storm MIT `main@fb951af7744dab086e34962e9bc6fe878e145f83`; Codebase Memory `storm`. **Question:** Where do multi-perspective personas come from, and what happens when the live web evidence they are induced from fails?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/storm_wiki/modules/persona_generator.py:get_wiki_page_title_and_toc` (:10–45) + `CreateWriterWithPersona.forward` (:77–111); consumer `knowledge_curation.py:StormKnowledgeCurationModule._get_considered_personas` (:281–284).
**Signature:** `get_wiki_page_title_and_toc(url) -> Tuple[str, str]`; `CreateWriterWithPersona.forward(topic, draft=None) -> dspy.Prediction(personas, raw_personas_output, related_topics)`.
**Data Shape:** Input: newline-separated LLM text containing raw Wikipedia URLs. Intermediate: `"Title: {title}\nTable of Contents: {toc}"` example blocks joined by `\n----------\n`. Output: numbered persona lines regex-parsed to strings `"Name: description"`.

### Decisive source
```python
# TOC indentation comes from a LEVEL STACK, not heading text:
while levels and level <= levels[-1]:
    levels.pop()
levels.append(level)
indentation = "  " * (len(levels) - 1)
toc += f"{indentation}{section_title}\n"      # h2/h3..h6 only; [edit] and \xa0 scrubbed
# boilerplate never becomes persona inspiration:
excluded_sections = {"Contents", "See also", "Notes", "References", "External links"}
# per-URL fail-soft: one dead link must not kill persona generation:
for url in urls:
    try:
        title, toc = get_wiki_page_title_and_toc(url)
        examples.append(f"Title: {title}\nTable of Contents: {toc}")
    except Exception as e:
        logging.error(f"Error occurs when processing {url}: {e}")
        continue
if len(examples) == 0:
    examples.append("N/A")                    # pipeline proceeds with no examples
# personas parsed from NUMBERED LLM lines only:
match = re.search(r"\d+\.\s*(.*)", s)
```

**Flow:** `find_related_topic` asks the LM for related topics and emits prose-with-URLs → every line containing "http" is harvested (`s[s.find("http"):]`, trailing junk tolerated) → each URL fetched+scraped fail-soft → surviving Title/TOC blocks become few-shot examples for `GenPersona` → numbered output lines regex-parsed → default "Basic fact writer" prepended upstream in `generate_persona`.
**Invariant:** (1) Persona induction NEVER throws on bad URLs — worst case is an `"N/A"` example block, so research always has ≥1 persona. (2) TOC hierarchy is computed by popping the level stack while `level <= top`, so skipped heading levels (h2→h5) still produce correct relative indentation. (3) The topic's own ground-truth URL is never among the scraped examples — induction uses RELATED pages only, keeping evaluation leakage out of the persona prompt. (4) Only lines matching `\d+\.` become personas — any other LLM chatter is silently dropped.
**Probe:** deterministic pins GREEN this pass — direct byte-reads of persona_generator.py:10–45 (`levels` stack + `excluded_sections` set), :88–99 (try/except-continue + `"N/A"` fallback), :107–110 (`\d+\.\s*` parse); knowledge_curation.py:281–284 delegation. Live retrieve `search_graph(project="storm", query="get_wiki_page_title_and_toc writer persona table of contents")` returned `persona_generator.get_wiki_page_title_and_toc :10-45` at rank 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "get_wiki_page_title_and_toc writer persona table of contents", limit: 10 });
```

## Verdict
Adopt fail-soft example harvesting + stack-derived indentation for any "induce perspectives from real documents" step; adapt the excluded-section vocabulary and the numbered-line output grammar; omit the requests/BeautifulSoup fetch specifics if your host already has a scraper. Caveat: no upstream tests exist at pin; source-pinned deterministic evidence.
