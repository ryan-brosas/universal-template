<!-- capsule-v2 -->
# Function-call edit contract — schema-declared line arrays with list/string dual coercion

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** If you adopt aider's deprecated tools-style edit format (replace_lines function), what wire contract and coercion rules must you preserve so GPT-3.5-era clients can't corrupt files?

## One function `replace_lines`; original/updated as line arrays; join-with-\n plus trailing-newline enforcement at apply time
**Path/Symbol:** `aider/coders/editblock_func_coder.py`: class-level `functions` JSON-schema block (:10-58, required explanation+edits; per-edit required path/original_lines/updated_lines), `__init__` RAISES RuntimeError (:61) — the class is deliberately non-instantiable pending get_edits/apply_edits refactor — `_update_files()` (:95-135), `get_arg(edit, arg)` (:138); `render_incremental_response` streams via `parse_partial_args()` (:87-93).
**Signature:** coercion: if `code_format == "list"` OR the value is already a list → `"\n".join(value)`; then any NON-EMPTY original/updated gets a `\n` appended if missing.
**Data Shape:** description pins semantics: "A unique stretch of lines from the original file, including all whitespace, without skipping any lines".

### Decisive source
```python
# gpt-3.5 returns lists even when instructed to return a string!
if self.code_format == "list" or type(original) is list:
    original = "\n".join(original)
...
if original and not original.endswith("\n"):
    original += "\n"
...
content = do_replace(full_path, content, original, updated)
if content:
    self.io.write_text(full_path, content)
```

**Flow:** tool-call arrives → name validated (`!= "replace_lines"` ⇒ ValueError) → partial args parsed for streaming preview → per-edit: admission check (`allowed_to_edit`), read file, reuse EditBlock's `do_replace` exact-match engine on the joined strings, write only on successful replacement else loud `Failed to apply edit to {path}`.
**Invariant:** empty-string edits are preserved (falsy guard skips newline-append but still applies) — creating an EMPTY file is legal while omitting the key raises via `get_arg`; failure to match leaves the file untouched (never truncate-on-mismatch).
**Probe:** deterministic anchor: `grep -nF 'gpt-3.5 returns lists' aider/coders/editblock_func_coder.py` → :113. Direct tests: the shared engine it calls is pinned by `tests/basic/test_editblock.py::test_replace_part` family executed GREEN this run via repo venv (`python -m pytest tests/basic/test_editblock.py -q`: **25 passed**).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "EditBlockFunctionCoder replace_lines", limit: 3 });
// rank-1: aider.aider.coders.editblock_func_coder.EditBlockFunctionCoder.__init__ (RuntimeError tombstone)
```

## Verdict
Adopt the SCHEMA + coercion rules if porting a tools-based editor; OMIT instantiating this legacy class (it self-destructs by design). The load-bearing lessons: declare uniqueness+whitespace in the schema text, coerce defensively at the boundary, and never write on match failure.
