<!-- capsule-v2 -->
# DocDetails validator chain — in what order do DOI normalization, bibtex generation, and field overwrite run?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** A DocDetails can be built from a provider payload, a manifest CSV row, or user data — what is the single ordered validation pipeline every construction path flows through, and why does order matter?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/types.py:DocDetails.validate_all_fields` (:1152-1184) orchestrating :populate_content_hash (:1141-1150), :lowercase_doi_and_populate_doc_id (:908-938), :remove_invalid_authors (:1008-1019), :misc_string_cleaning (:959-964), :inject_clean_doi_url_into_data (:966-980), :add_preprint_journal_from_doi_if_missing (:982-1006), :populate_bibtex_key_citation (:1036-1139), :overwrite_docname_dockey_for_compatibility_w_doc (:1021-1034).
**Signature:** `@model_validator(mode="before") def validate_all_fields(cls, data)`.
**Data Shape:** Raw dict (possibly stringified `authors`/`other` via `ast.literal_eval`, possibly stringified `fields_to_overwrite_from_metadata` from CSV) → fully-derived dict. `AUTOPOPULATE_VALUE = ""` is the sentinel meaning "derive me".

### Decisive source
```python
data = cls.populate_content_hash(data)          # md5 file_location if missing; None preserved
data = cls.lowercase_doi_and_populate_doc_id(data)   # strip https://doi.org/ + lower; doc_id = md5(doi.lower()+content_hash)[:16]
data = cls.remove_invalid_authors(data)         # cull None / "et al" authors
data = cls.misc_string_cleaning(data)           # pages "--"→"-", spaces stripped
data = cls.inject_clean_doi_url_into_data(data) # force modern doi.org URL
data = cls.add_preprint_journal_from_doi_if_missing(data)  # 10.48550→ArXiv, 10.1101+len25→BioRxiv, len27→MedRxiv...
data = cls.populate_bibtex_key_citation(data)   # key=author[:50]+year+title3[:100] scrubbed; incomplete bibtex merged w/ SELF_GENERATED provenance; citation=None cleared when overwrite-listed
return cls.overwrite_docname_dockey_for_compatibility_w_doc(data)  # LAST: key→docname, doc_id→dockey per fields_to_overwrite_from_metadata
```

**Flow:** Bibtex regeneration only fires when `not bibtex or not is_bibtex_complete(...)` (complete = has `doi=` AND `title=`); existing-but-incomplete entries are parsed and MERGED (`merge_bibtex_entries`, entry2 preferred) with `BibTeXSource.SELF_GENERATED` appended to `other.bibtex_source`. Citation re-renders from bibtex via pybtex `unsrtalpha` with `CITATION_FALLBACK_DATA` ("Unknown author(s)" etc.) only when `citation is None`.
**Invariant:** `fields_to_overwrite_from_metadata` (default {key, doc_id, docname, dockey, citation, content_hash}) gates BOTH the citation-clear and the final overwrite — providers must not silently stomp caller-supplied identity; the preprint journal sniff checks DOI LENGTH because 10.1101 is shared by bio*Rxiv siblings.
**Probe:** `tests/test_paperqa.py::test_docdetails_deserialization` (:2833), `::test_docdetails_doc_id_roundtrip` (:2892); clients-side `test_arxiv_doi_is_used_when_available` (test_clients.py:779).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "validate_all_fields populate_bibtex_key_citation lowercase_doi", limit: 10 });
```
**Retrieve:** graph resolves all eight static validators on DocDetails; `get_code_snippet` for the chain.

## Verdict
Adopt the ordered chain and the overwrite-gating concept wholesale — reordering breaks derived-field consistency; adapt the preprint DOI-prefix table to your domains; omit pybtex rendering if you store citations as plain strings (but keep the completeness gate). Direct tests upstream pin deserialization + roundtrip.
