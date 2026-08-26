<!-- capsule-v2 -->
# Outline grammar coercion — how do you turn free-form LLM outline text into a strict `#`-heading tree?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What normalization must LLM outline output undergo before a tree parser can trust it?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/utils.py:ArticleTextProcessing.clean_up_outline` (:457-503) + consumers `StormArticle.from_outline_str` (storm_dataclass.py:438-474) and `WriteOutline.forward` (outline_generation.py:108-121).
**Signature:** `clean_up_outline(outline: str, topic: str = "") -> str`.
**Data Shape:** Input: markdown-ish text with `#`/`##` headings and `-` bullets; output: pure heading lines (`#`-prefixed), bullets PROMOTED to subsection headings, topic line and tail sections removed.

### Decisive source
```python
if topic != "" and f"# {topic.lower()}" in stripped_line.lower():
    output_lines = []          # RESET: drop everything up to the real content start
if stripped_line.startswith("#"):
    current_level = stripped_line.count("#")
    output_lines.append(stripped_line)
elif stripped_line.startswith("-"):
    output_lines.append("#" * (current_level + 1) + " " + stripped_line[1:].strip())
# then strip wiki-tail sections, DOTALL until next heading:
outline = re.sub(r"#[#]? See also.*?(?=##|$)", "", outline, flags=re.DOTALL)  # x12 variants:
# See Also / Notes / References / External links / External Links /
# Bibliography / Further reading* / Further Reading* / Summary / Appendices / Appendix
outline = re.sub(r"\[.*?\]", "", outline)     # strip bracket links/citations
```

**Flow:** Line-scan resets the buffer when the topic-heading echo appears → headings recorded with their level → bullets converted into level+1 headings using the CURRENT level → twelve regexes amputate Wikipedia-style tail sections (See also/Notes/References/External links/Bibliography/Further reading/Summary/Appendix...) from their heading to the next heading or EOF → any remaining `[...]` stripped. The parser side then tolerates a leading topic line (`adjust_level`) and skips duplicate topic-named sections.
**Invariant:** (1) Bullet promotion depends on the most recent HEADING — an outline starting with bullets attaches them under level 0+1. (2) The topic reset is a substring match on lowercased text, so it also fires on `## Topic:` echoes mid-outline. (3) Tail-section regexes use non-greedy `.*?` with lookahead — they remove the section's CONTENT too, which is why they must run after bullet promotion. (4) `from_outline_str` counts `#` per line and pops a node stack while `level <= top` — malformed level jumps become siblings, never errors.
**Probe:** executed lifted probe GREEN — T04: topic reset, `- point` → `## point`, "See also" section and its junk dropped (scratch-storm-pass1/probe_gate5.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "clean_up_outline See also Notes References", limit: 10 });
```

## Verdict
Adopt the promote-and-amputate ladder for any outline-then-tree pipeline; adapt the banned-section vocabulary; omit nothing — feeding raw outlines to a stack parser is the failure this capsule prevents. Caveat: no upstream tests; probe executed against lifted class source.
