<!-- capsule-v2 -->
# Detailed-report subtopic loop — how does a host assemble a multi-subtopic report without duplicating already-written content, and when do subtopic URLs enter the bibliography?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** When porting a host that fans one research run into per-subtopic child researchers, what global state must be threaded, how is context deduplicated across children, and in what order do URLs become references?

## DetailedReport.run + _get_subtopic_report global-state threading
**Path/Symbol:** `backend/report_type/detailed_report/detailed_report.py:84-91` (`run`), `:122-136` (`_hashable_context`), `:138-195` (`_get_subtopic_report`), `:197-205` (`_construct_detailed_report`).
**Signature:** `async def run(self) -> str`; `_get_subtopic_report(self, subtopic: Dict) -> Dict[str, str]` returning `{"topic", "report"}`.
**Data Shape:** four globals threaded through the loop — `global_context: List[str|dict]`, `global_urls: Set[str]` (seeded from source_urls), `global_written_sections: List[dict]`, `existing_headers: List[{"subtopic task", "headers"}]`. Context items may be dicts (MCP shape `{title, body|content}`) or strings.

### Decisive source
```python
# detailed_report.py:84-91 — merge order: subtopic URLs fold into visited_urls BEFORE references render
    await self._initial_research()
    subtopics = await self._get_all_subtopics()
    report_introduction = await self.gpt_researcher.write_introduction()
    _, report_body = await self._generate_subtopic_reports(subtopics)
    self.gpt_researcher.visited_urls.update(self.global_urls)
    report = await self._construct_detailed_report(report_introduction, report_body)
```
```python
# detailed_report.py:122-136 — dict context stringified so set-dedup works on mixed shapes
    for item in input_context:
        if isinstance(item, dict):
            title = item.get("title", "No title")
            content = item.get("body", item.get("content", ""))
            context_str = f"Title: {title}\nContent: {content}"
            context_items.append(context_str)
        else:
            context_items.append(str(item))
```
```python
# detailed_report.py:149-164 — child shares the URL set; context seeded DEDUPED from parent
            visited_urls=self.global_urls,
...
        subtopic_assistant.context = list(set(self._hashable_context(self.global_context)))
        await subtopic_assistant.conduct_research()
```

**Flow:** initial research on the main researcher → subtopics planned (see subtopics-fallback-shape-asymmetry) → introduction written ONCE from main context → per subtopic: fresh `GPTResearcher(report_type="subtopic_report", parent_query=self.query, visited_urls=self.global_urls, mcp_configs/mcp_strategy propagated, max_search_results override re-applied to child cfg)` → child context pre-seeded with `list(set(_hashable_context(global_context)))` → child conducts research (shared visited_urls means it never re-visits a parent URL) → draft section titles generated → titles parsed via `extract_headers` → similar ALREADY-WRITTEN contents retrieved by draft-title similarity against `global_written_sections` → child writes its report with `existing_headers` + `relevant_written_contents` (the dedup-aware subtopic prompt, see report-prompt-ladder-collapse-retry) → loop accumulates: `global_written_sections.extend(extract_sections(report))`, `global_context` REPLACED by the child's own context, `global_urls.update(child.visited_urls)`, `existing_headers.append({task, headers})` → after the loop, `visited_urls.update(global_urls)` then assembly `intro + TOC + body + conclusion-with-references` (references appended to the conclusion text only).
**Invariant:** dedup is TWO-sided and both sides are required: retrieval-side (similar written contents fetched per draft title) feeds prompt-side uniqueness instructions — dropping either lets later subtopics repeat earlier ones. URL sharing works by ALIASING, not copying: `GPTResearcher.__init__` uses the passed set verbatim (`self.visited_urls = visited_urls or set()`, agent.py:161) and `_initial_research` binds `global_urls` to the main researcher's set, so main + every child share ONE set object and the explicit `visited_urls.update(global_urls)` at :89 is a defensive no-op at this pin — if your host COPIES the set into children instead, you must keep an update-before-reference-rendering step or subtopic-only URLs vanish from the bibliography. Context seeding must stringify dicts BEFORE set-dedup or MCP-shaped items never compare equal.
**Probe:** byte anchors verified at pin: detailed_report.py:89 (update-before-assembly), :122-136 (hashable context), :149/:164 (shared set + deduped seed), :186-193 (four-way accumulation), :200-202 (references on conclusion only); agent.py:161 (set used verbatim), :627-650 (get_similar_written_contents_by_draft_section_titles delegation), :700-731 (extract_headers/extract_sections/table_of_contents wrappers). Coverage caveat: NO upstream test pins the subtopic loop (tests/test_websocket_manager.py only stubs `DetailedReport` as an empty class) — probe is source-read only; runner BLOCKED in-lane (missing aiofiles, read-only checkout).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "_get_subtopic_report _hashable_context global_written_sections existing_headers", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reference-shared URL set, the stringify-then-set-dedup context seed, the two-sided dedup (retrieval of similar written contents + prompt-side uniqueness instructions), and the update-before-references ordering — each closes a concrete duplication or missing-citation failure mode. Adapt the four-global threading to your host's state container; keep the "replace context with the newest child's context" rule or later subtopics drift toward the original query. Omit the backend/FastAPI envelope; the loop is host-agnostic.
