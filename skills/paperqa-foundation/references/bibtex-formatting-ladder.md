<!-- capsule-v2 -->
# Bibtex formatting ladder — how does raw provider bibtex become a rendered citation even when fields are missing?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How are provider bibtex strings cleaned (@None, @['Article']), missing fields injected (authors as Person objects!), failures degraded to title-only or "Ref {key}", and keys regenerated?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/utils.py:format_bibtex` (:314-368), `clean_upbibtex` (:272-311), `create_bibtex_key` (:434-450), `bibtex_field_extract` (:409-428), `BIBTEX_MAPPING` (:553-585); S2 usage `semantic_scholar.py:176-186`; Crossref key rewrite `crossref.py:doi_to_bibtex` (:115-164).
**Signature:** `def format_bibtex(bibtex, key=None, clean=True, missing_replacements=None) -> str`.
**Data Shape:** Type-normalization tables: Semantic Scholar labels (`JournalArticle`→article, `Preprint`→article...) in clean_upbibtex; Crossref content types (`journal-article`→article, `book-chapter`→inbook, `posted-content`→misc...) in BIBTEX_MAPPING. Key grammar: `author[:50] + year + title-first-3-words[:100]` with FORBIDDEN_KEY_CHARACTERS stripped.

### Decisive source
```python
try:
    entry = bd.entries[key]
except KeyError as exc:      # key may be a non-empty PREFIX — recover first prefix match
    try:
        entry = next(iter(v for k, v in bd.entries.items() if k.startswith(key) and key))
    except StopIteration:
        raise CitationConversionError(...)
try:
    for field, replacement_value in missing_replacements.items():
        if field == "author" and "author" not in entry.persons:
            tmp_author_bibtex = f"@misc{{tmpkey, author={{{replacement_value}}}}}"
            authors = Parser().parse_string(tmp_author_bibtex).entries["tmpkey"].persons["author"]
            for a in authors: entry.add_person(a, "author")     # authors need Person parsing!
        elif field not in entry.fields:
            entry.fields.update({field: replacement_value})
    return style.format_entry(label="1", entry=entry).text.render_as("text")
except (FieldIsMissing, UnicodeDecodeError):
    try: return entry.fields["title"]       # degrade to bare title
    except KeyError as exc: raise CitationConversionError(...)
```

**Flow:** Crossref's x-bibtex endpoint returns publisher-formatted entries; paper-qa rewrites the KEY deterministically from author/year/title fragments (`data.replace(key, new_key, 1)` — FIRST occurrence only). S2 prefers its own citationStyles.bibtex (provenance SEMANTIC_SCHOLAR), falls back to Crossref by DOI (provenance CROSSREF), else self-generated. `@['Type']` bracketed forms and `@None` normalized pre-parse.
**Invariant:** Author injection MUST go through pybtex Person parsing (plain string fields break name rendering); provenance lists accumulate in `other.bibtex_source` so downstream can distrust self-generated citations.
**Probe:** clients tests `test_title_search`/`test_doi_search` assert rendered citation shapes (test_clients.py:121/:273); executed grep pins `data.replace(key, new_key, 1)` crossref.py:164 and author-Person branch utils.py:347-356.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "format_bibtex clean_upbibtex create_bibtex_key doi_to_bibtex", limit: 10 });
```

## Verdict
Adopt table-driven type normalization + prefix-key recovery + Person-aware author injection; adapt fallback text to your locale; omit Crossref roundtrip if providers always emit complete bibtex. Coverage caveat: rendering needs pybtex installed; logic verified by source + cited tests.
