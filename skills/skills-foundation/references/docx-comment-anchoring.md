<!-- capsule-v2 -->
# DOCX Comment Anchoring — which parts make a comment real, and when does a written comment stay invisible?

**Source:** anthropics/skills (docx skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the minimal complete set of package changes to add a Word comment programmatically, and what anchors it to text?

## Six cross-linked parts + range markers
**Path/Symbol:** `skills/docx/scripts/comment.py` — directory mode + .docx-direct mode; documented at `skills/docx/SKILL.md` lines 76-87.
**Signature:** `python scripts/comment.py unpacked/ "Comment text" [--parent 0]` | `python scripts/comment.py contract.docx "Text" -o annotated.docx`.
**Data Shape:** Writes 6 things: `comments.xml`, `commentsExtended.xml`, `commentsIds.xml`, `commentsExtensible.xml`, the relationships part, and the content-type overrides. Templates for each ship in `scripts/templates/*.xml`. Comment IDs auto-assigned.

### Decisive source
```markdown
Comments require six cross-linked files. Use the helper — directory mode when
you'll also be editing `document.xml` (saves an unzip/rezip cycle),
`.docx`-direct mode otherwise:
...
The script writes `comments.xml`, `commentsExtended.xml`, `commentsIds.xml`,
`commentsExtensible.xml`, the relationships, and the content-type overrides.
Comment IDs are auto-assigned. It then prints the `<w:commentRangeStart>`/
`<w:commentRangeEnd>`/`<w:commentReference>` snippet to add to
`word/document.xml` so the comment anchors to specific text — until you place
those markers, the comment exists but is not visible.
```

**Flow:** Helper writes the six parts into the package → prints a marker snippet referencing the new comment ID → porter inserts `commentRangeStart`/`commentRangeEnd` around the target run(s) plus a `commentReference` run in document.xml → rezip → only then does Word render the anchored comment.
**Invariant:** All six parts are jointly required (a comments.xml alone yields an invalid/inert package); the anchor lives in document.xml, not in comments.xml — omitting the marker snippet leaves an invisible orphan comment rather than failing loudly.
**Probe:** `python skills/docx/scripts/comment.py <dir-or-docx> "test" ` prints the exact marker snippet; observable behavior: before insertion of printed markers, output opens with no visible comment; after insertion, the comment attaches to the chosen range.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "comment commentsExtended content-type", limit: 10 });
```

## Verdict
Adopt: the six-part completeness rule and the invisible-without-anchor invariant — both generalize to any OOXML annotation feature (they come from the ECMA-377 packaging model). Adapt template XMLs and ID assignment to your generator. Omit the people.xml people-part nuance unless targeting full Word fidelity. Caveat: verified against the script's own docstring/behavior; no unit tests in-repo.
