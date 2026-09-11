<!-- capsule-v2 -->
# Article-tree markdown parser — how do you rebuild a section tree from flat markdown with a level stack?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How does `parse_article_into_dict` nest sections, and what are the stack rules a porter must reproduce?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/utils.py:ArticleTextProcessing.parse_article_into_dict` (:553-594); consumers `StormArticle.from_string`, `update_section` (via `insert_or_create_section`), polish re-ingestion (article_polish.py:47-49).
**Signature:** `parse_article_into_dict(input_string: str) -> Dict[title, {"content": str, "subsections": Dict}]`.
**Data Shape:** Root dict's `subsections` maps top-level headings; every node holds accumulated non-heading lines as `content` and nested dicts under `subsections`.

### Decisive source
```python
lines = [line for line in input_string.split("\n") if line.strip()]
root = {"content": "", "subsections": {}}
current_path = [(root, -1)]                      # stack of (node, level), root sentinel -1
for line in lines:
    if line.startswith("#"):
        level = line.count("#")
        title = line.strip("# ").strip()
        new_section = {"content": "", "subsections": {}}
        while current_path and current_path[-1][1] >= level:
            current_path.pop()                   # pop until strict parent (smaller level)
        current_path[-1][0]["subsections"][title] = new_section
        current_path.append((new_section, level))
    else:
        current_path[-1][0]["content"] += line + "\n"
```

**Flow:** Blank lines dropped → heading lines push/pop the level stack (`>=` pops so same-level siblings replace nothing but attach to the correct parent) → text lines append to whichever node is on top. `insert_or_create_section` then folds this dict into the live tree: existing section names UPDATE content in place; missing ones are created; `trim_children=True` deletes children absent from the incoming dict; a section named "summary" at root is inserted at the FRONT (:233-238).
**Invariant:** (1) Duplicate titles at different branches coexist (dicts keyed per-parent) — only same-parent duplicates overwrite. (2) Level jumps (h1 → h3) attach h3 under h1 directly. (3) `content` accumulates WITH trailing newlines; consumers must `.strip()` (both call sites do). (4) Polish writes `# summary` + lead FIRST, so re-parsing keeps summary as first child — order matters because `to_string()` emits pre-order.
**Probe:** executed lifted probe GREEN — T05: `# H1 / text / ## H1.1 / text / # H2 / text` nests H1.1 under H1, contents land on the right nodes (scratch-storm-pass1/probe_gate5.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "parse_article_into_dict header level stack", limit: 10 });
```

## Verdict
Adopt the `(node, level)` stack verbatim for markdown→tree ingestion; adapt the content accumulation if you need per-line metadata; omit the front-insertion special case unless your articles have leads. Companion: `clean_up_section` (:506-538) drops `In summary/Overall/In conclusion` paragraphs and whole Summary/Conclusion sections (probe T07 GREEN). Caveat: no upstream tests; probes executed against lifted class source.
