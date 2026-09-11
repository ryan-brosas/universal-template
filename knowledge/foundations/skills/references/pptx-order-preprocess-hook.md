<!-- capsule-v2 -->
# pptx presentation-order preprocess hook — which schema-legal order does the validator enforce, and why?

**Source:** anthropics/skills Apache-2.0/source-available `main@3b3fad96`; Codebase Memory `skills`. **Question:** pptxgenjs writes `sldIdLst` before `notesMasterIdLst` — why does that pass PowerPoint but fail the XSD, and what does the validator do about it?

## Repair-in-memory toward the XSD's notes-before-slides order
**Path/Symbol:** `skills/pptx/scripts/office/validators/pptx.py` (`PPTXSchemaValidator._preprocess_for_schema` :209-227); schema truth `office/schemas/ISO-IEC29500-4_2016/pml.xsd` CT_Presentation sequence (:1055-1059).
**Signature:** `_preprocess_for_schema(xml_doc, relative_path) -> xml_doc` (base no-op; pptx overrides).
**Data Shape:** `pml.xsd CT_Presentation` child ORDER: `sldMasterIdLst? → notesMasterIdLst? → handoutMasterIdLst? → sldIdLst?` — i.e. **notesMasterIdLst MUST precede sldIdLst**.

### Decisive source
```python
# pptx.py:210-211 — only one part is touched:
if relative_path.as_posix() != "ppt/presentation.xml":
    return xml_doc
# :218-226 — if notes sits AFTER slides, move it BEFORE sldIdLst:
children = list(root)
if children.index(notes) < children.index(slides):
    return xml_doc            # already XSD-valid: leave alone
root.remove(notes)
root.insert(list(root).index(slides), notes)
```
XSD pin (executed grep @3b3fad96): pml.xsd :1055-1059 lists `sldMasterIdLst`, then `notesMasterIdLst`, then `handoutMasterIdLst`, then `sldIdLst`.

**Flow:** generator emits slides-first (`<p:sldIdLst>` immediately after `<p:sldMasterIdLst>`) → XSD validation would flag sequence violation → preprocess hook detects `index(notes) > index(slides)` and MOVES notes before sldIdLst in the in-memory copy → XSD passes → disk file keeps pptxgenjs order, which PowerPoint accepts unmodified but refuses once reordered by hand.
**Invariant:** the hook repairs ONLY `ppt/presentation.xml`, only the notes/slides pair; it mutates the throwaway copy used for validation, never the shipped bytes. A porter who "fixes" their generator to match the XSD literally must re-run the corruption ladder — hand-reordering `<p:presentation>` children is a documented corruption rule.
**Probe:** build a presentation root with `[sldIdLst, notesMasterIdLst]` and call `_preprocess_for_schema(tree, Path("ppt/presentation.xml"))`; children come back `[notesMasterIdLst, sldIdLst]`; an already-notes-first tree and any other part name are returned untouched. Executed @3b3fad96 (scratch-docs-p6-probes.py P5a/P5b/P5c).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "_preprocess_for_schema", limit: 5 });
```

## Verdict
Adopt: when a generator emits schema-illegal-but-tool-tolerated XML, validate against a repaired in-memory copy instead of failing or rewriting output. Adapt the hook point (`_preprocess_for_schema`) to your validator architecture. Omit if your generator already emits notes-first. Coverage caveat: no upstream tests; behavior executed live at the pin.
