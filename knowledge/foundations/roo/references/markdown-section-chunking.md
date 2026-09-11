<!-- capsule-v2 -->
# Markdown section chunking — how do .md files ride the code-index pipeline without a grammar?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** How is markdown decomposed into blocks, and which lines can be silently dropped?

## Header-split sections + pre/post-header content
**Path/Symbol:** `src/services/code-index/processors/parser.ts:parseMarkdownContent/processMarkdownSection` (:452-533; :394-450).
**Signature:** `processMarkdownSection(lines: string[], filePath, fileHash, type, seenSegmentHashes, startLine: number, identifier: string | null = null): CodeBlock[]`.
**Data Shape:** `parseMarkdown(content)` (tree-sitter markdownParser) returns capture pairs — `name.definition` + `definition` sharing ONE header node; type becomes `markdown_header_h${level}` parsed from the capture name via `/\.h(\d)$/`.

### Decisive source
```ts
const startLine = definitionCapture.node.startPosition.row + 1
const endLine = definitionCapture.node.endPosition.row + 1
const sectionLines = lines.slice(startLine - 1, endLine)   // header line EXCLUDED from its own section
...
if (lastProcessedLine < lines.length) { /* tail after last header → markdown_content */ }
```

**Flow:** no headers ⇒ whole file as one `markdown_content` block. With headers: pre-first-header lines become their own block; each definition span becomes a section block carrying the header TEXT as identifier and level-suffixed type; trailing content after the last section becomes a final `markdown_content` block. Sections larger than 1150 chars (or with any oversized line) fall into the same line-chunk kernel; the identifier is then copied onto EVERY produced chunk.
**Invariant / trap:** `lastProcessedLine = endLine` where endLine is 1-BASED inclusive, but the tail slice uses `lines.slice(lastProcessedLine)` (0-based) — the net effect drops ONE boundary line between the last section and the tail. A naive port that "fixes" one side of this off-by-one either duplicates the boundary line or widens the hole; reproduce both halves exactly or recompute spans consistently.
**Probe:** `src/services/code-index/processors/__tests__/parser.spec.ts` ("should process markdown files alongside code files" lives in scanner.spec :253-330 — end-to-end .md/.markdown handling); executed pins: type template + pre-header/tail branches.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "parseMarkdownContent processMarkdownSection markdown_header", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt header-level-typed sections with identifier propagation through chunking, and pre/post-header content blocks. Adapt the capture source if your host has a real markdown AST. Omit the tree-sitter mock-capture machinery (covered by markdown-mock-captures capsule). Caveat: the boundary-line drop is confirmed by line-math on the pinned source, not by a dedicated spec.
