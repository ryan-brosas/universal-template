<!-- capsule-v2 -->
# OOXML Unpack-Edit-Rezip Pipeline — how is an existing .docx/.pptx/.xlsx edited safely?

**Source:** anthropics/skills (docx/pptx/xlsx skills, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the shared, corruption-avoiding pipeline for editing an existing Office Open XML package in place?

## unzip → sanitize → edit → zip-from-inside → validate(--original)
**Path/Symbol:** `skills/docx/SKILL.md` "Editing existing documents" (lines 49-58); `skills/pptx/SKILL.md` "Editing existing decks and templates" (line 64+); XML-parse rule at pptx line 74; validators `skills/docx/scripts/office/validators/base.py` (`BaseSchemaValidator`, 24-871) + `validate.py`.
**Signature:** `(cd unpacked && rm -f ../out.docx && zip -Xr ../out.docx .)` · `python scripts/office/validate.py out.docx --original doc.docx [--auto-repair] [--author <name>]`.
**Data Shape:** OOXML package = ZIP of XML parts + `_rels/` relationships + `[Content_Types].xml`.

### Decisive source
```bash
unzip -q doc.docx -d unpacked/
find unpacked -type l -delete   # strip symlink entries — docx from external parties is untrusted
python scripts/merge_runs.py unpacked/
# edit unpacked/word/document.xml in place — do NOT reformat or pretty-print
(cd unpacked && rm -f ../out.docx && zip -Xr ../out.docx .)
python scripts/office/validate.py out.docx --original doc.docx   # XSD checks
```
```markdown
If you script an XML transform, parse with `defusedxml.minidom` — round-tripping
OOXML through `xml.etree.ElementTree` rewrites namespace prefixes and corrupts
the deck.
```

**Flow:** Unzip quietly → delete symlink entries (zip-bomb/path-trust defense for files from external parties) → optional format-specific normalization (merge_runs for docx text findability) → edit the target part IN PLACE preserving bytes everywhere else → from INSIDE the dir, rm any stale output then `zip -Xr ../out.<ext> .` → schema-validate against the XSDs bundled under `scripts/office/schemas/` with `--original` baselining template-inherited errors away.
**Invariant:** Never pretty-print/reformat OOXML (whitespace in text nodes is content); rezip from inside the directory after rm or deleted parts survive in the archive; ElementTree must never round-trip these files (namespace-prefix rewrite = corrupt deck); template-derived outputs always pass `--original` because the template's own XSD violations otherwise read as yours.
**Probe:** `python skills/docx/scripts/office/validate.py out.docx --original doc.docx` exits clean on a valid edit; observable behavior: removing `--original` on a template-derived file reports pre-existing template failures; zipping without `rm` first leaves ghost parts listed by `unzip -l`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "BaseSchemaValidator validate", limit: 10 });
```

## Verdict
Adopt the whole pipeline verbatim — it is environment-independent packaging hygiene. Adapt validator entry points to your tree (the same office/ validators are vendored into docx, pptx, AND xlsx skills — one implementation, three copies). Omit the XSD corpora (~40 schema files) if you call LibreOffice validation instead. Caveat: no unit tests; the validators themselves are the executable probe.
