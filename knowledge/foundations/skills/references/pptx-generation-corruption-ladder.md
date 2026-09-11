<!-- capsule-v2 -->
# PPTX Generation Corruption Ladder — which generator options silently corrupt a deck or get charts discarded?

**Source:** anthropics/skills (pptx skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** When creating .pptx with pptxgenjs (or any OOXML writer), which option values produce files PowerPoint refuses to open — and how are they caught before shipping?

## Hard corruption rules + mandatory post-write validation
**Path/Symbol:** `skills/pptx/SKILL.md` "Creating with pptxgenjs — gotchas" (corruption bullets at lines 30-56; chart faults at 46-47); validator `skills/pptx/scripts/office/validators/pptx.py` (`PPTXSchemaValidator`, 13-437).
**Signature:** `python scripts/office/validate.py deck.pptx [--original src.pptx]` — run after EVERY `writeFile()`.
**Data Shape:** pptxgenjs writes `<p:notesMasterIdLst>` immediately after `<p:sldIdLst>` with both masters sharing one theme part — valid but fragile ordering that PowerPoint accepts only unmodified.

### Decisive source
```markdown
- **Hex colors: never `#`, never 8 digits.** ... Both `"#FF0000"` and alpha
  baked into the hex (`"00000020"`) **corrupt the file**. For translucency:
  `transparency: 0-100` on fills and images, `opacity: 0.0-1.0` on shadows.
- **Shadow `offset` must be ≥ 0** — a negative offset corrupts the file.
- **On a stacked bar or column chart, `dataLabelPosition` must be `ctr`,
  `inEnd`, or `inBase`.** `outEnd` **corrupts the file**.
- **A combo series using `secondaryValAxis`/`secondaryCatAxis` needs both
  `valAxes` and `catAxes` on the chart options, two entries each.** Without
  them pptxgenjs writes axis *ids* it never declares, and PowerPoint
  **discards that chart** and reports the file as corrupt.
- **Never reorder the children of `<p:presentation>`.**
- **After `writeFile()`, run `python scripts/office/validate.py deck.pptx`.**
```

**Flow:** Generate with the constraint ladder in mind → write file → run schema+structural validator (it "reports the two chart faults above and the slide-XML defects PowerPoint refuses, and names the fix for each") → fix in the GENERATOR, never by hand-editing packed XML → rebuild → revalidate.
**Invariant:** Silent-failure classes to design around: (a) corrupting values (`#`/8-digit hex, negative shadow offset, outEnd on stacked) — other tools still open the file so only PowerPoint reveals the fault; (b) discarded-output faults (undeclared axis ids) — python-pptx opens it, LibreOffice renders it, XSD passes it, PowerPoint drops the chart; therefore validator-after-every-write is non-negotiable. Also silent-ignore traps: `letterSpacing` ignored (`charSpacing` is real), transparency-vs-opacity applied per element type, mutated shared option objects (fresh object per add* call).
**Probe:** Build a deck with `dataLabelPosition:"outEnd"` on a stacked column and run the bundled validator — it flags the exact defect ("each failure names its fix"); the same file passes python-pptx open + LibreOffice render while PowerPoint reports corruption.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "PPTXSchemaValidator slide checks", limit: 10 });
```

## Verdict
Adopt: the corruption ladder as an input-validation checklist for ANY OOXML-writing code, and validate-immediately-after-write with generator-side fixes. Adapt specific option names if you use a different writer library (the classes of fault — illegal attribute values, undeclared relationship ids, fragile part ordering — transfer). Omit pptxgenjs-specific API trivia when not using it. Caveat: pinned by prose + validator behavior; no unit tests upstream.
