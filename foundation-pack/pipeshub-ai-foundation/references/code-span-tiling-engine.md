<!-- capsule-v2 -->
# Code span tiling engine — how do you chunk a source file so every byte lands in exactly one retrievable block (no gaps, no double-counted definitions) across 18 grammars with ONE walker?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What is the structural trick that makes byte-exact file coverage a guarantee instead of a per-language hope — and which symbol-extraction shortcuts would break it?

## One recursive walk whose symbols come out of the tiling pass, not beside it
**Path/Symbol:** `backend/python/app/modules/parsers/code_parser/engine.py:parse_code/_Walker` (L546–583 entry, L187–540 walker; whole file 583L).
**Signature:** `parse_code(source: bytes, language: str) -> ParsedFile`; internals `_get_parser(cfg)`, `decode_source(raw) -> bytes`, `_Walker._scope/_collect/_classify/_tile/_emit`.
**Data Shape:** In: raw bytes + config name. Out: `ParsedFile(language, symbols[], parse_error_line|None, skipped_reason|None)` where every `ParsedSymbol(kind, name, start_line, end_line, parent_chain, text, decorators, parent, is_container)` covers a contiguous slice; filler kinds (`imports/statements/comment/header`) tile between definitions. Unknown language → empty ParsedFile; >5 MiB → `skipped_reason="oversized"`.

### Decisive source
```python
# engine.py module docstring — THE invariant, stated structurally:
# "Every symbol it emits comes out of the tiling pass, which is what makes
#  the byte-exactness guarantee structural rather than incidental: a
#  definition found off the tiling path would overlap the span that already
#  covers it and double-count those bytes."
def _tile(self, spans, scope_start, scope_end, *, is_container):
    ...
    # Whitespace attaches backward: each span runs to the start of the next,
    # so blank lines never become blocks of their own.
    for i in range(len(tiled) - 1):
        tiled[i].end = tiled[i + 1].start
    tiled[0].start = scope_start
    tiled[-1].end = scope_end
```

**Flow:** `decode_source` normalises invalid UTF-8 via latin-1 round-trip (tree-sitter indexes BYTE offsets) → `_get_parser` returns a FRESH Parser bound to a cached Language (Parser holds mutable mid-parse state; only Language is cached under `_PARSER_LOCK`, double-checked) → `_Walker.walk` calls `_scope(root, 0, len(src))`: collect named children into spans → `_tile` makes them cover the scope exactly (gap classify: container-leading gap = `header` [decorators+signature+docstring], else comment-run vs statements; BOM stripped as whitespace; overlapping spans clipped forward; whitespace absorbed backward) → `_emit` numbers every span as a ParsedSymbol and recurses into containers only when `_has_members`.
**Invariant:** (1) Symbols are ONLY emitted from spans that survived `_tile` — adding a second extraction path re-introduces overlap and double-counted bytes. (2) Comments attach FORWARD to what they document (≤1 blank line gap, `_COMMENT_ATTACH_MAX_BLANK_LINES`); a trailing same-line comment absorbs BACKWARD into the preceding span; detached runs become their own block. (3) Only a TYPE container promotes inner functions to methods (`method_container_kinds` excludes namespace/mod) — a C++ namespace function stays a function. (4) A container without member definitions never becomes a group (`_has_members` must route class attributes through `_as_field`, because a Python attribute is an `assignment` wrapped in `expression_statement` — type-matching the child misses every attribute-only class). (5) Partially-broken files still yield usable symbols above the break: `root.has_error` sets `parse_error_line` via `_first_error_line`, which walks ALL children (unnamed missing tokens carry errors that `named_children` hides) and takes the MIN error line.
**Probe:** `backend/python/tests/unit/modules/parsers/code_parser/test_exhaustiveness.py` — byte-exact reconstruction for 13 synthetic shapes + 18 per-language samples (:61/:91), missing-trailing-newline twins (:97), ≥1 named definition per grammar (:103 — tiling alone is satisfied by one big statements block, this catches wrong node-type configs), unique qualified names (:114), all grammars actually load under the pinned tree-sitter ABI (:122), container children tile the container (:146), real-repo files re-tiled byte-exact for .py/.ts/.tsx/.js up to 120 files each (:233).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "parse_code" --detail ids
codebase-memory-mcp cli trace_path --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --function-name parse_code --direction inbound --depth 3 --include-tests true   # callers_total=120
```

## Verdict
Adopt whole: the walker+tiler pair is directly portable to any RAG-over-source pipeline (chunking that can never lose or duplicate bytes is the property vector search silently depends on). Adapt `_KIND_SOURCES`/name-node vocab if your grammars differ; keep the ordered `_KIND_SOURCES` precedence (method_types beats function_types when a grammar lists a node in both). Omit the per-language docstring extraction (lives in code_file_parser, see code-block-mapper capsule). Coverage caveat: none material — this is the best-tested seam in the package (dedicated exhaustiveness suite pins tiling, naming, ABI drift, and real-file reconstruction).
