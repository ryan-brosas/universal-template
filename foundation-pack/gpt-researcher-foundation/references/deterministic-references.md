<!-- capsule-v2 -->
# Deterministic references — why is the References section sorted, and what did set iteration break?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How must a visited-URL bibliography be rendered so identical inputs produce identical reports?

## add_references sorted rendering
**Path/Symbol:** `gpt_researcher/actions/markdown_processing.py:94-116` (`add_references`); header/section/TOC siblings `:4-92`.
**Signature:** `def add_references(report_markdown: str, visited_urls: set) -> str`
**Data Shape:** Appends `\n\n\n## References\n\n` + one `- [url](url)` line per URL; any exception returns the ORIGINAL report unchanged.

### Decisive source
```python
# Sort so the reference list is deterministic. ``visited_urls`` is a
# set, whose iteration order varies from run to run (and across
# processes), which made the final report's References section
# non-reproducible for the same inputs.
url_markdown += "".join(f"- [{url}]({url})\n" for url in sorted(visited_urls))
```

**Flow:** report body + sorted reference block → callers pass `researcher.visited_urls` straight from the shared dedup set. The markdown helpers around it (`extract_headers` via python-markdown HTML with an `(node, level)`-style stack; `extract_sections` regex `<h\d>(.*?)</h\d>(.*?)(?=<h\d>|$)` DOTALL; `table_of_contents` 4-space indent recursion) are all pure functions safe to lift.
**Invariant:** sorting is the ONLY thing making byte-reproducible output possible given a set input — dropping it reintroduces run-to-run diffs that break snapshot tests and diff-based review. Failure handling is fail-open (return input) so a formatting bug never destroys the report.
**Probe:** `tests/test_add_references_order.py::test_add_references_renders_in_sorted_order` + `test_add_references_stable_across_equivalent_sets`; battery P13a GREEN.
