<!-- capsule-v2 -->
# PPTX orphan GC — how do you garbage-collect an unpacked deck without ever nuking a live one?

**Source:** anthropics/skills (source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What does clean.py treat as garbage, what two sanity guards refuse to run, and why does deletion loop to a fixed point?

## Cascade collector with refusal guards (`pptx/scripts/clean.py`, whole file)
**Path/Symbol:** `skills/pptx/scripts/clean.py` — `clean_unused_files` (:253–282), `remove_orphaned_slides` (:67–127), `get_slides_in_sldidlst` (:44–60), `remove_orphaned_files` (:183–230), `update_content_types` (:233–250).
**Signature:** `clean_unused_files(unpacked_dir: Path) -> list[str]` (removed rel paths); raises `RefusedToClean` (:63–64, "The package does not look the way a readable package should.").
**Data Shape:** identity of a slide = BASENAME of the part resolved from presentation.xml.rels (`posixpath.basename(rid_to_slide[rid])`, :56–60); resource sweep covers media/embeddings/charts/diagrams/tags/drawings/ink + theme*.xml(+rels) + notesSlides.

### Decisive source
```python
# :78-90 — refuse when sldIdLst names slides but NOTHING on disk matches
if on_disk and not any(s.name in referenced_slides for s in on_disk):
    listed = re.findall(r'<p:sldId[^>]*r:id="([^"]+)"', ...)
    if listed:
        raise RefusedToClean(
            f"<p:sldIdLst> lists {len(listed)} slide(s) and none of the "
            f"{len(on_disk)} slide(s) on disk match any of them. ...")
# :268-275 — rels and targets orphan EACH OTHER: iterate to fixed point
while True:
    removed_rels = remove_orphaned_rels_files(unpacked_dir)
    referenced = get_referenced_files(unpacked_dir)
    removed_files = remove_orphaned_files(unpacked_dir, referenced)
    if not removed_rels + removed_files:
        break
```

**Flow:** global guard first (`:256–260`: .rels exist but NO relationship resolves to a part ⇒ RefusedToClean "Refusing to treat every file as unreferenced") → drop slides whose basename is absent from the sldIdLst set (+their per-slide .rels), then prune matching SLIDE_REL_TYPE relationships from presentation.xml.rels → delete `[trash]/` wholesale → fixed-point cascade (deleting a chart XML orphans its .rels; deleting a .rels orphans its target; repeat until a full pass removes nothing) → only if something was removed, strip matching `Override PartName` entries from [Content_Types].xml. CLI maps `(RefusedToClean, ValueError)` to exit 1 with **"Nothing was deleted."** (:297–302).
**Invariant:** Both guards run before destructive phases, so a mis-parse can never masquerade as an empty deck; an EMPTY sldIdLst does NOT trip the deck guard (all slides legitimately orphaned). Content-Type DEFAULTS are never touched — only Overrides for exactly removed paths. Slides are matched by basename after opc resolution, so `../slides/slide5.xml` and `slide5.xml` are the same slide.
**Probe:** No upstream tests exist repo-wide (validator-family precedent). Deterministic anchors (executed this pass):
`grep -c 'Refusing to treat every file as unreferenced' skills/pptx/scripts/clean.py` = 1;
`grep -c 'this is a parse failure, not an empty deck' skills/pptx/scripts/clean.py` = 1;
`grep -n 'while True:' skills/pptx/scripts/clean.py` → line 268 inside clean_unused_files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "RefusedToClean remove_orphaned_slides fixed point", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: guard-before-delete discipline, basename-based slide identity via resolved OPC targets, cascade-to-fixed-point collection, Override-only content-types repair, "Nothing was deleted." atomicity message. Adapt: the hardcoded resource-dir list to your package family's part taxonomy. Omit: nothing structural — but note it deletes `[trash]/` unconditionally once guards pass. Deepens (does not duplicate) pptx-slide-registration-ordering, which cites only the RefusedToClean symbol.
