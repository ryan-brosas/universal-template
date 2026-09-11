<!-- capsule-v2 -->
# PPTX Slide Registration & Ordering — why must duplication/deletion/reorder precede content edits, and what does hand-copying break?

**Source:** anthropics/skills (pptx skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the safe procedure for restructuring an existing deck (duplicate/delete/reorder slides), and which invariants does the package bookkeeping enforce?

## add_slide.py registration + structural-work-first ordering
**Path/Symbol:** `skills/pptx/scripts/add_slide.py` (duplicates slide or slideLayoutN.xml with all package bookkeeping), `skills/pptx/scripts/clean.py` (`RefusedToClean`, 63-64; deletes parts unreferenced by `<p:sldIdLst>`); rules at `skills/pptx/SKILL.md` lines 66-67.
**Signature:** `python scripts/add_slide.py unpacked/ slide2.xml [--after slideN.xml]` | `add_slide.py deck.pptx slide2.xml -o out.pptx`; `python scripts/clean.py unpacked/`.
**Data Shape:** A registered slide = part file + `[Content_Types].xml` override + presentation.xml.rels relationship + `<p:sldId>` entry in `<p:sldIdLst>`. Duplicated slides still REFERENCE source chart/SmartArt/embedded-object parts rather than cloning them.

### Decisive source
```markdown
- **Do all structural work — add, delete, reorder — before editing any
  slide's content.** `add_slide.py` copies a slide file verbatim, so
  duplicating after you edit clones the edited content; and `clean.py`
  deletes any slide missing from `<p:sldIdLst>`, including one you just
  wrote.
- **Never copy a slide file by hand** — `add_slide.py` does every
  registration a new slide needs ... **pass `-o`, or it rewrites the input
  deck in place.** A duplicated slide still *references* its source's
  chart/SmartArt/embedded-object parts rather than cloning them, so editing
  one slide's chart changes the other's.
```

**Flow:** Thumbnail the template to pick layouts → duplicate needed slides via add_slide.py → reorder/delete by editing `<p:sldIdLst>` in ppt/presentation.xml → run clean.py to drop orphaned slides/media/rels ONLY once sldIdLst is final → then edit slide content → validate.
**Invariant:** Structural operations are order-coupled with content edits (duplication clones current bytes; clean prunes unregistered slides); a hand-copied slide file is unregistered — invisible to the presentation until its four bookkeeping entries exist; shared-part references mean duplicated slides are not independent until charts/media are re-embedded.
**Probe:** `add_slide.py deck.pptx slide2.xml -o out.pptx` prints `Created ppt/slides/slide17.xml from slide2.xml`; observable behavior: without `-o` it rewrites the INPUT deck in place; after deleting a slide from sldIdLst, `clean.py` removes the orphaned part and its rels.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "add_slide duplicate slide registration", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "skills", query: "RefusedToClean clean", limit: 5 });
```

## Verdict
Adopt: structural-before-content ordering and the registration completeness set — both derive from OOXML packaging, not pptxgenjs, so they transfer to any deck-editing tooling. Adapt the specific scripts' CLI to your harness. Omit python-pptx workaround details unless you use that library (it cannot duplicate slides at all). Caveat: no unit tests upstream; scripts are their own behavioral probe.
