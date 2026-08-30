<!-- capsule-v2 -->
# Docstring & signature metadata ladder — how do you lift per-language documentation into retrieval metadata without attaching the WRONG comment (or missing the docstring behind an annotated signature)?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How do you extract signatures, docstrings and subtokens per language so every code block carries retrievable identity metadata — and which regex scoping rules stop body comments from masquerading as docs?

## Style-dispatched extraction over the symbol's OWN text; anchoring and search-position are load-bearing
**Path/Symbol:** `backend/python/app/modules/parsers/code_parser/code_file_parser.py:_extract_signature/_extract_docstring/_leading_line_comment/_subtokenise` (L79–98 / L104–130 / L88–102 / L73–77; constants L36–52).
**Signature:** `_extract_signature(text: str) -> str | None`; `_extract_docstring(text: str, language: str) -> str | None` (dispatches on `cfg.docstring_style`: `python | block_comment | line_comment | none`); `_subtokenise(text: str) -> str`.
**Data Shape:** In: the span text of ONE symbol (already byte-tiled by the engine — see code-span-tiling-engine) + language name. Out: signature ≤300 chars (`_MAX_SIGNATURE_CHARS`), docstring ≤500 chars (`_MAX_DOCSTRING_CHARS`, `None` when absent), space-joined sorted unique subtokens. Metadata lands in `CodeMetadata.signature/docstring/decorators` per block/group (see code-block-mapper).

### Decisive source
```python
# Terminal-on-its-line colon: only optional whitespace or a trailing comment
# may follow before the newline — so `def f(data: dict[str, Any]) -> list[str]:`
# (param annotations full of colons) still finds the REAL signature end.
_PY_SIG_COLON_RE = re.compile(r":[^\S\n]*(?:#[^\n]*)?\n")
# Anchored: a doc comment introduces what follows it. An unanchored search
# picks up a `/** ... */` buried in a body, and grammars that nest a trailing
# comment inside the previous declaration (Groovy) would hand every member the
# next member's documentation.
_BLOCK_DOC_RE = re.compile(r"\A\s*/\*\*(.*?)\*/", re.DOTALL)

def _extract_signature(text):
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(_NON_SIGNATURE_PREFIXES):  # @,#,//,/*,* ,--,[
            continue
        return stripped[:_MAX_SIGNATURE_CHARS]
```

**Flow:** Signature = FIRST line that isn't blank and doesn't start with a non-signature prefix (comments, decorators, Rust/C#/Swift attribute syntaxes `[`), truncated at 300 → Docstring by style: (a) `python` — find the body-opening colon via `_PY_SIG_COLON_RE`, search `_PY_DOCSTRING_RE` (optional r/b/u prefixes, triple-quote pair backreference) ONLY AFTER `sig_end.end()` so parameter annotations can't hide or fake the docstring; (b) `block_comment` — `\A`-ANCHORED `/**…*/`, star-stripped per line; (c) `line_comment` — `_leading_line_comment` collects the opening run of prefix lines (`///`,`//`,`---`,`--`,`#` per config), skipping blanks BEFORE the run but STOPPING at the first blank after it, joined with spaces; style `none` → `None`. Subtokens: `_SUBTOKEN_RE = [A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|\d+`, lowercased, length>2, deduped, sorted — stored alongside block text purely to improve BM25 recall on camelCase/snake_case identifiers.
**Invariant:** (1) Extraction reads ONLY the symbol's own tiled text — never the whole file — because attachment correctness was already decided by the tiler (comment-forward absorption); re-deciding here double-attaches. (2) The Python colon regex must be terminal-on-line: a greedy first-colon search returns garbage for any annotated signature (direct-test-pinned). (3) Block-doc anchoring is `\A`: unanchored extraction silently hands every member of a Groovy/Java class the NEXT member's docs (grammar nests trailing comments inside the previous declaration) — the most expensive wrong-metadata failure because it looks plausible. (4) Line-comment runs stop at the first internal blank line: docs separated from their definition by a blank belong to nothing (mirrors the tiler's `_COMMENT_ATTACH_MAX_BLANK_LINES=1`). (5) Caps (300/500) bound metadata size independent of block size — adapt to your embedding budget, never drop.
**Probe:** `backend/python/tests/unit/modules/parsers/code_parser/test_code_file_parser.py::test_docstring_extraction_with_annotated_signature` (:109–114 — `"Transform data into strings."` recovered past `dict[str, Any]` annotations); `tests/unit/modules/parsers/code_parser/test_exhaustiveness.py::test_class_header_holds_decorator_signature_and_docstring` (:165–176 — header block holds decorator+signature+docstring together); per-language samples exercise every style through the ≥1-named-definition and tiling suites.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"_extract_docstring docstring_style signature","detail":"ids","limit":5}'
```

## Verdict
Adopt the three-style dispatch with its two scoping laws (terminal-on-line colon for Python; `\A`-anchored block docs everywhere) — both fail silently and plausibly when ported wrong. Adapt the caps and the prefix vocabularies (`_NON_SIGNATURE_PREFIXES`, per-config `doc_line_prefixes`) to your languages. Omit the subtokeniser only if your index already tokenises identifiers. Coverage caveat: line_comment and none styles ride the per-language sample suites rather than a dedicated unit test.
