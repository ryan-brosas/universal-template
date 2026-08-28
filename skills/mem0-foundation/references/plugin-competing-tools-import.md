<!-- capsule-v2 -->
# Competing-tools import + export round-trip — how do you ingest rival tools' config files and parse an export file back into records?

**Source:** mem0 Apache-2.0 `main@7e096155714c`. **Question:** when migrating memory/context from other AI tools (and round-tripping your own exports), how does the importer pick a splitter per source, and what grammar does the export parser implement?

## Subcommand importer + block parser (import_competing_tools.py, parse_export_file.py)
**Path/Symbol:** `integrations/mem0-plugin/scripts/import_competing_tools.py:COMMANDS` (lines 268–273) + `import_chunks` (95–119); `integrations/mem0-plugin/scripts/parse_export_file.py:parse_blocks` (lines 37–89) + `_parse_frontmatter` (92–104).
**Signature:** `import_chunks(chunks, api_key, user_id, project_id, branch, source, hash_key="") -> int`; `parse_blocks(content: str) -> list[dict]`.
**Data Shape:** four subcommands — cursorrules (`.cursorrules`, split on `"## "`), copilot (`.github/copilot-instructions.md`, split on `"## "`), cline (`memory-bank/` dir, one whole-file chunk per non-empty .md), continue (`.continue/rules.md`, `split_by_hr_or_headers`); hash key `{project_id}:{source}:{path}` in `~/.mem0/import_hashes.json`; metadata `{type:"project_profile", source:"<cmd>-import"}`, `infer=False`, role="user". Export format: blocks delimited by lines matching `(?m)^---\s*$`; odd split-indices = frontmatter, even = content; records `{id, type, confidence, branch, files[], categories[], content, created_at?}`.

### Decisive source
```python
    raw_blocks = re.split(r"(?m)^---\s*$", content)
    # frontmatter blocks are at odd indices (1, 3, 5, ...) and
    # content blocks at even indices (2, 4, 6, ...).
    i = 1
    while i < len(raw_blocks):
        frontmatter_raw = raw_blocks[i]
        content_raw = raw_blocks[i + 1] if i + 1 < len(raw_blocks) else ""
        fm = _parse_frontmatter(frontmatter_raw)
        memory_content = content_raw.strip()
        if not memory_content:
            i += 2
            continue
```
and the importer's skip gate:
```python
    if hash_key:
        combined = "\n".join(chunks)
        current_hash = _content_hash(combined)
        hashes = _load_hashes()
        if hashes.get(hash_key) == current_hash:
            print(f"Already imported (unchanged) -- skipping: {hash_key}")
            return 0
```
**Flow:** importer: subcommand dispatch (`sys.argv[1]` must be in COMMANDS, else usage + exit 0) → `--path` parsed both as `--path v` and `--path=v` → identity resolved (no key ⇒ stderr message, NO API call) → file/dir existence checked before any call → split per-source → `filter_and_truncate` → hash-skip → POST chunks (hash persisted only when success > 0). Parser: normalize CRLF → split on exact `---` lines → pair frontmatter/content from index 1 → first-colon `key: value` grammar (values may contain colons — timestamps survive) → comma-list fields → skip empty-content blocks → JSON to stdout; `-` reads stdin; any error path prints `[]` and exits 0.
**Invariant:** the splitter choice IS the format contract — cursorrules/copilot use `## ` headers (preamble becomes chunk 0), cline treats each memory-bank .md as one atomic memory, continue splits on HR or headers; no fallback re-splitting across sources. role="user" is correct here because these files are human-authored (the capture hooks' assistant-role rule does not apply — test_message_roles.py pins the boundary). The parser's `^---\s*$` regex requires the delimiter to be a WHOLE line, so `---` inside content or a `---` horizontal rule with trailing text never splits. Every failure path exits 0 with `[]`/usage — both tools are safe to call from scripts.
**Probe:** `tests/test_import_competing_tools.py` (13 tests — splitter units incl. 50/10000 char boundaries, mock-API body assertions: `app_id` top-level, `infer is False`, `source` per subcommand, cline skips empty.md, no-key/missing-file never call urlopen, unknown subcommand exits 0) and `tests/test_parse_export_file.py` (12 tests — single/multi block, missing optional fields, empty-content filtering, round-trip against the export skill's exact format, multiline content, colon-in-value, CLI subprocess + `[]` error paths). Both files executed GREEN this pass: 29 passed total with test_message_roles.py.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "import competing tools parse export blocks frontmatter", limit: 10, fields: ["signature", "lines"] });
```
Recorded for graph-connected sessions; MCP not connected this pass (DEGRADED path, whole-file direct reads + 29 executed tests instead).

## Verdict
Adopt the per-source splitter dispatch (format decides splitter, never a generic one) and the whole-line `---` block grammar with first-colon frontmatter for export round-trips. Adapt the subcommand set, chunk boundaries (50/10000), and hash-key composition to your host. Omit the mem0 endpoint/auth shape. Coverage: both files read whole; 25 direct tests executed GREEN across the two files.
