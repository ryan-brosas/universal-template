<!-- capsule-v2 -->
# CsvFile RFC 4180 normalization — how do you store LLM-written CSV without corrupting it?

**Source:** browser-use MIT `main@85ddbfedf609166b2d2c76c3d80506649fee82a9`; Codebase Memory `mnt-hdd-utopia-inspo-agents-browser-use`. **Question:** how does the filesystem guarantee well-formed CSV when the model writes malformed rows?

## Parse-and-reserialize write hook
**Path/Symbol:** `browser_use/filesystem/file_system.py:168-229` (`CsvFile`; `_normalize_csv` :180-214, overridden `write_file_content` :216, `append_file_content` :220).
**Signature:** `_normalize_csv(raw: str) -> str` (staticmethod); overrides run inside every `write`/`append` before the disk sync.
**Data Shape:** input arbitrary LLM text; output re-serialized CSV with `\n` line terminator and trailing newline stripped (callers own final line endings).

### Decisive source
```python
# Detect double-escaped LLM tool call output: if the content has no real
# newlines but contains literal \n sequences ... Unescape \" → " first, then \n → newline
if '\n' not in stripped and '\\n' in stripped:
    stripped = stripped.replace('\\"', '"')
    stripped = stripped.replace('\\n', '\n')
reader = csv.reader(io.StringIO(stripped))
rows = [row for row in reader if row]        # drop blank-line artifacts
out = io.StringIO()
writer = csv.writer(out, lineterminator='\n')
writer.writerows(rows)
return out.getvalue().rstrip('\n')
```

**Flow:** strip surrounding newlines → unescape double-escaped JSON output when there are no real newlines → parse through `csv.reader` (fixes unquoted commas, internal quotes, inconsistent empties by construction) → drop fully-empty rows → re-serialize via `csv.writer`. Append path normalizes the new chunk first, joins with existing content (inserting a missing trailing `\n`), then re-normalizes the COMBINED text.
**Invariant:** normalization happens on EVERY write/append (never at read time), so stored `.content` is always canonical; empty/blank append chunks are a no-op (:223-224); if parsing yields zero rows the ORIGINAL raw string is returned unchanged (:207-208).
**Probe:** `tests/ci/infrastructure/test_filesystem.py::TestBaseFile::test_csv_file_disk_operations` (:158) — round-trips `'name,age,city\nJohn,30,New York'` to disk byte-exact through `CsvFile.write`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-browser-use", query: "CsvFile _normalize_csv csv.reader writerows", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the normalize-on-write hook plus the double-escape detector for any agent scratch CSV. Adapt which repairs you apply (the escape heuristic is tuned to LLM tool-call output). Omit nothing — skipping the combined-text re-normalization on append leaves mixed quoting between old and new rows.
