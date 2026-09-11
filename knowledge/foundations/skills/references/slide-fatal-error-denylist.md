<!-- capsule-v2 -->
# Slide XML Fatal-Error Denylist — which lxml schema errors mean "PowerPoint will refuse this file", and what happens for unlisted error classes?

**Source:** anthropics/skills (office/helpers/pptx_slide.py, byte-identical in pptx/docx/xlsx skills; source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** How does the pipeline decide whether a validation error is ship-stopping or ignorable?

## Curated denylist over raw lxml messages
**Path/Symbol:** `skills/docx/scripts/office/helpers/pptx_slide.py` (`FATAL_SLIDE_ERRORS` :17–48 — seven (regex, human-meaning) pairs; `SLIDE_PART_RE` :12–14; `is_schema_verdict` :51; `fatal_slide_errors` :53–60).
**Signature:** `fatal_slide_errors(errors: set[str]) -> list[str]`; `is_schema_verdict(error: str) -> bool` (True iff message starts with `"Element "`).
**Data Shape:** input = set of raw lxml/validate error strings from schema-validating unpacked slide XML (`ppt/slides|slideLayouts|slideMasters|notesSlides|notesMasters|handoutMasters/*.xml`); output = translated fatal subset with meaning prepended.

### Decisive source
```python
"""Pick the slide-XML schema errors PowerPoint refuses the file over.

A denylist over lxml's messages, so an unrecognised error class is a miss
rather than a false alarm.
"""
```
```python
(re.compile(r"\}tableStyleId': This element is not expected"),
 "two <a:tableStyleId> in one <a:tblPr> (the schema allows one)"),
```

**Flow:** validate slide part XML → feed every error string through fatal_slide_errors → each regex hit is translated to a fixable diagnosis (duplicate tableStyleId; non-six-hex srgbClr val; empty txBody; lim="NaN" line join; misplaced uLnTx / overrideClrMapping; empty nvGrpSpPr) → NO match = not reported as fatal. The seven entries are exactly the corruption classes observed to make PowerPoint reject otherwise-openable decks.
**Invariant:** Denylist semantics are deliberate: unknown errors NEVER block shipping (a miss, not a false alarm) — the inverse of a fail-closed allowlist. This only makes sense because the caller already schema-validates; the denylist filters that superset down to the empirically-fatal minority. Each entry encodes one real repair (e.g. keep exactly one tableStyleId in tblPr).
**Probe:** No unit tests upstream. Deterministic probe: pass an error string containing `}srgbClr', attribute 'val'` → expect the colour diagnosis; pass `Element foo: unexpected` variants matching no pattern → expect empty output.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "fatal_slide_errors", limit: 5 });
```

## Verdict
Adopt the denylist approach + the seven entries for any slide-XML QA gate. Re-derive entries empirically if porting to a different validator (messages are lxml-specific). Omit nothing. Caveat: pinned by whole-file read; triple-vendored copies verified identical by md5.
