<!-- capsule-v2 -->
# Code block mapper — how do spans become a retrievable block tree with stable identities (and why do groups keep their whole body)?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What does the parser→platform boundary look like — where do IDs get minted, what makes a symbol addressable, and which retrieval-cost trade-offs are deliberate?

## Two-pass placement over parser-layer types; identity is `kind:dotted.scope` or line-range
**Path/Symbol:** `backend/python/app/modules/parsers/code_parser/code_file_parser.py:CodeFileParser.parse_to_blocks/_to_container` + module fn `qualified_name_for` (L55–66, L154–232; whole file 332L); parser-layer models in `code_parser/models.py:ParsedSymbol/ParsedFile/FILLER_KINDS/HEADER_KIND`.
**Signature:** `CodeFileParser().parse_to_blocks(content: bytes, record_name: str, file_path=None, language=None) -> BlocksContainer | None`; `qualified_name_for(kind, name, parent_chain, *, start_line=None, end_line=None) -> str`; satisfies the `IParser` protocol (`async parse(content, record_name, config) -> ParseResult`).
**Data Shape:** `None` return means SKIPPED (oversized) — callers must fall back to an alternative parser, never treat it as empty; unknown language → EMPTY container (a real "nothing indexable" result). Blocks and block_groups are numbered in SEPARATE index spaces (`placement: dict[int, tuple[is_group, idx]]` wires them). `BlockGroup.data = {text, kind, start_line, end_line}` + `content_hash`; `Block.data` adds `subtokens`.

### Decisive source
```python
def qualified_name_for(kind, name, parent_chain=(), *, start_line=None, end_line=None):
    """``"{kind}:{dotted.scope}"`` -- the human-readable identity of a symbol.
    Unnamed spans are addressed by line range instead (``imports:L1-5``)."""
    if name:
        return f"{kind}:{'.'.join([*parent_chain, name])}"
    ...
# models.py on the chain itself:
# Full chain of enclosing container names, outermost first. Truncating this
# to one level collapses Outer.Inner.run onto Outer.run and silently
# collides symbol IDs.

def _build_group(self, sym, index, language, parent_group=None):
    # A container keeps its whole body. Its children are subsets of it, which
    # costs nothing in vectors: vectorstore only embeds table/view groups, so
    # a code group's text never reaches Qdrant.
```

**Flow:** Pass 1 turns every memberful container into a BlockGroup (nested containers get their own group — Outer.Inner keeps its level instead of collapsing onto Outer) → pass 2 parents every other symbol's block to its NEAREST enclosing GROUP via `_nearest_group` walking `sym.parent` past non-group ancestors (a function nested in a method attaches to the class group) → one RECORD_SUMMARY block appended last (`"{record} ({lang}) — kind:name, …"` over top-level named symbols). Identity/metadata per symbol: `_extract_signature` = first non-comment/decorator line capped at 300 chars; `_extract_docstring` per-language style (python regex AFTER the signature colon so annotated params can't hide it; anchored `/**…*/` so Groovy's nested trailing comments don't hand every member the NEXT member's docs; leading `//`-run for line-doc languages); `_subtokenise` splits camelCase/snake_case into BM25-recall tokens.
**Invariant:** (1) ID minting happens HERE and only here ("the only place that knows the file's repo-relative path") — parser-layer types carry plain names+lines, no graph IDs. (2) Qualified names are unique within a file (test-pinned); unnamed filler spans are addressed by `kind:L<start>[-end]`, which SHIFTS when lines move above them while named symbols keep their identity. (3) Group bodies duplicate their children's text BY DESIGN and stay embed-free because only table/view groups get embedded — collapsing this would either lose class-level retrieval or double-embed code. (4) Determinism: same bytes → same qualified names AND content_hashes (test-pinned).
**Probe:** `backend/python/tests/unit/modules/parsers/code_parser/test_code_file_parser.py` :29–36 full parent chain (`method:Outer.Inner.run`), :39–45 determinism, :48–57 nested-group wiring (`children.block_group_ranges`/`block_ranges`), :60–71 local vars are not fields (`LIMIT`=field, `local` absent), :74–82 imports coalesce into ONE block whose text IS the source run, :85–88 unknown language → empty, :91–95 broken syntax still yields symbols + parse_error_line, :99–106 IParser contract, :109–114 docstring extraction under annotated signatures.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "CodeFileParser parse_to_blocks qualified_name_for" --detail ids
codebase-memory-mcp cli trace_path --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --function-name parse_code --direction inbound --depth 2   # FileContentParser/Processor/chatbot/OCR all funnel here
```

## Verdict
Adopt the two-pass mapper, the separate-index-space placement map, nearest-group parenting, and the `kind:dotted.scope` identity scheme for any AST→retrievable-block pipeline. Adapt block/group container types to your platform model and the 300/500-char metadata caps to your embedding budget. Omit the subtokeniser if your chunker already rides a token-overlapping index. Coverage caveat: none material — dedicated suite covers every branch incl. determinism and broken-input degradation.
