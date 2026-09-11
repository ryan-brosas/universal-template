<!-- capsule-v2 -->
# Validator CLI contract — which families validate, which are refused, and what does --author really do?

**Source:** anthropics/skills Apache-2.0/source-available `main@3b3fad96`; Codebase Memory `skills`. **Question:** what does `validate.py` actually gate per OOXML family, and why can a broken xlsx exit 0?

## Family routing, deliberate refusals, author-as-mark
**Path/Symbol:** `skills/docx/scripts/office/validate.py` (`main` :48-169; `_has_tracked_changes` :36-45; `_fail` :31-33).
**Signature:** `python validate.py <path> [--original <file>] [--auto-repair] [--author NAME] [-v]`; path = packed office file OR unpacked dir.
**Data Shape:** `OOXML_FAMILY` maps `.docx/.dotx→docx`, `.pptx/.potx→pptx`, `.xlsx/.xltx→xlsx` (helpers/__init__.py); packed input is unpacked via `safe_extract` to a temp dir.

### Decisive source
```python
# :142-148 — the xlsx family is REFUSED but GREEN:
case "xlsx":
    print("No XSD schema validation is performed for xlsx-family files ... "
          "use scripts/recalc.py instead.")
    sys.exit(0)
# :84-85 — author requires original:
if args.author is not None and not args.original:
    _fail("--author requires --original")
# :75-81 — author marks the run; it NEVER filters:
"...the name marks the run as redlining work and is not used to filter."
# :133-137 — tracked-changes hint when nobody asked for the check:
elif original_file and _has_tracked_changes(unpacked_dir):
    print("Note: this document has tracked changes; they were not checked...")
```

**Flow:** family from suffix (original wins over path) → unpack if packed → docx: DOCXSchemaValidator (+RedliningValidator iff `--author`) → pptx: PPTXSchemaValidator only → xlsx: print pointer to recalc.py, **exit 0** → validators run repair-then-validate (`--auto-repair` repairs first, rezips in place if packed) → final rc 0/1.
**Invariant:** "exit 0" from this tool means "no XSD opinion" for xlsx — workbook health lives ONLY in recalc.py's gate (`errors_found` still exits 0 there too; a missing `status` key means nothing ran). `--author` changes WHAT is checked (adds redlining), never WHOSE changes are excluded. The tracked-changes note fires whenever ins/del elements exist un-checked.
**Probe:** pack a minimal `.xlsx` (just `[Content_Types].xml` + rels) and run `python3 skills/docx/scripts/office/validate.py t.xlsx` from the REPO ROOT (anchored at `skills/docx/scripts/office/`, not repo root — the script path is skill-relative); expect rc=0 with the recalc.py sentence on stdout. Executed @3b3fad96: rc=0 + "For formula-error checking, use scripts/recalc.py instead." ERRATUM: originally shipped as `python scripts/office/validate.py t.xlsx` — wrong anchor dir; the script lives under `skills/docx/scripts/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "No XSD schema validation is performed", limit: 5 });
```

## Verdict
Adopt the routing table (docx full+optional-redlining, pptx schema-only, xlsx refused-green→recalc.py) for any multi-family document validator. Adapt extension map to your host's template suffixes. Omit `--author` unless porting redlining workflows. Coverage caveat: no upstream tests; probe executed live against the real CLI.
