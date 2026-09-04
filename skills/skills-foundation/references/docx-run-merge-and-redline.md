<!-- capsule-v2 -->
# DOCX Run Merge & Redline — why does find-and-replace on raw .docx XML miss visible text, and what structure must tracked changes preserve?

**Source:** anthropics/skills Apache-2.0-adjacent (docx skill is source-available, LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** How is .docx text made findable for editing, and what are the exact OOXML rules for wrapping tracked deletions?

## Run coalescing + tracked-change XML contract
**Path/Symbol:** `skills/docx/scripts/merge_runs.py` — module docstring + `merge_runs(input_dir)`; called from `skills/docx/SKILL.md` edit pipeline (line 54); redlining rules pinned at SKILL.md line 63.
**Signature:** `python merge_runs.py unpacked/` | `python merge_runs.py doc.docx -o merged.docx`.
**Data Shape:** Input `word/document.xml`; output same file with adjacent identically-formatted `<w:r>` elements coalesced, rsid attributes and proofErr markers stripped, `<w:t>` (+ `<w:delText>` inside deletions) consolidated. Rendering unchanged.

### Decisive source
```python
"""Merge adjacent identically-formatted runs in a DOCX.

Word fragments paragraph text across many <w:r> elements (revision ids,
spell-check markers, editing history), which makes find-and-replace on
word/document.xml unreliable — the string you're looking for is split
across runs. This coalesces adjacent runs whose formatting (<w:rPr>) is
identical ... Rendering is unchanged.
...
Runs in two different <w:ins>/<w:del> wrappers are never merged: that would
rewrite tracked-change structure, collapsing separate revisions into one.
"""
```
And from the SKILL.md (the porter's trap list):
```markdown
Wrap runs in `<w:ins>`/`<w:del>` with `w:id`, `w:author`, `w:date` attributes.
Inside `<w:del>`, the text element is `<w:delText>`, not `<w:t>`. A deleted
paragraph mark ... means "merge this paragraph into the next" — so deleting a
paragraph outright is that plus a `<w:del>` around every run. The `<w:del/>`
must come before the rPr's other children; their order is schema-enforced.
```

**Flow:** unzip → delete symlink entries (untrusted input) → `merge_runs.py` to make text contiguous → edit document.xml in place → validate with `office/validate.py --original doc.docx --author <redline-name>` which reports any changed text lacking `<w:ins>`/`<w:del>` wrappers.
**Invariant:** Never merge runs across different revision wrappers; never reformat or pretty-print document.xml (whitespace inside `<w:t>` is content); deleted-paragraph semantics = deleted mark joins paragraphs (an emptied paragraph vanishing is an artifact of pandoc/LibreOffice accept views, not a document defect — check the XML).
**Probe:** `skills/docx/scripts/merge_runs.py` accepts both unpacked dir and .docx directly (`-o out.docx`); observable behavior: identical `<w:rPr>` neighbors become one run with concatenated text while `<w:ins>/<w:del>` boundaries remain intact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "merge_runs delText", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "skills", query: "RedliningValidator", limit: 5 });
```

## Verdict
Adopt: run-coalescing before any XML search/replace, the `<w:delText>`/deleted-mark/ordering rules, author-attributed redline validation — these encode Word's real behavior. Adapt paths/helpers (`office.helpers` rezip utilities) to your tree. Omit LibreOffice-specific accept-changes quirks unless you ship an accept pipeline. Caveat: no unit tests in-repo; probes are behavioral via the scripts themselves.
