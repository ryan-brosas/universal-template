<!-- capsule-v2 -->
# Docname & text-validity plumbing — how does a free-text citation become a stable docname, and when is parsed text "not a document"?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How are MLA citations converted to collision-free docnames (and what token wins?), and what entropy/length gates decide an upload is garbage BEFORE embedding costs are paid?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/utils.py:citation_to_docname` (:612-629), `maybe_is_text` (:68-90), `maybe_is_pdf/maybe_is_html` (:93-102); consumers `docs.aadd` :215-222 (`_get_unique_name` suffix ladder :84-91) and validity gate :313-335.
**Signature:** `def citation_to_docname(citation: str) -> str`; `def maybe_is_text(s: str, thresh: float = 2.5) -> bool`.
**Data Shape:** Docname ladder: FIRST `[A-Z][a-z]+` TitleCase token → else first `[A-Z0-9]{2,}` acronym → else `Doc{md5(citation)[:8]}` (deterministic — regression-tested against UUID drift). Year = LEFTMOST `\d{4}` anywhere. Collisions resolved by `_get_unique_name` single-letter suffixes a,b,c...

### Decisive source
```python
match = re.search(r"([A-Z][a-z]+)", citation)      # NOTE: sentence-initial words match!
if match is not None: author = match.group(1)
else:
    match = re.search(r"([A-Z0-9]{2,})", citation)
    author = match.group(1) if match is not None else f"Doc{hexdigest(citation)[:8]}"
year = ""
match = re.search(r"(\d{4})", citation)
if match is not None: year = match.group(1)
return f"{author}{year}"
# entropy gate: MAX_TEXT_ENTROPY=8.0 ceiling; spaces EXCLUDED from counting because
# PDF title pages encode layout as space runs ("PDF parsing sometimes represents
# horizontal distances between words ... with spaces")
return MAX_TEXT_ENTROPY > entropy > thresh
```

**Flow:** docs.aadd validity check combines: texts non-empty, first chunk ≥10 chars, first-two-chunks de-newlined ≥20 chars, AND maybe_is_text over the first FIVE chunks (title pages skew entropy). All three magic sniffers read 4 bytes then seek(0) — callers may pass unseekable-ish streams safely after wrap.
**Invariant:** The porter trap: "Smith et al." mid-sentence LOSES to a leading "In" — the ladder takes the first regex hit in string order; digits belong to the SAME acronym class so `"12345 2019"` yields `123451234` (leftmost 4 of the run, not a clean year). Direct tests pin both.
**Probe:** `tests/test_utils.py::test_citation_to_docname_acronym_title` (CD47/SIRPα→"CD472022"), `::test_citation_to_docname_non_text_fallback_is_deterministic`; executed lifted probes T7a-T7c + T6a-T6c GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "citation_to_docname maybe_is_text _get_unique_name", limit: 10 });
```

## Verdict
Adopt ladder order + deterministic hash fallback + space-excluded entropy window verbatim; adapt thresholds for your PDF extractor; omit HTML/PDF magic-byte sniffing if inputs are pre-typed. Probes executed GREEN incl. upstream's own two unit tests' exact fixtures.
