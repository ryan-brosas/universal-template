<!-- capsule-v2 -->
# WorkspaceFilesystem `.py` write validation — how do you reject broken Python scripts WITHOUT rejecting valid scripts that agents indent by mistake?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** An LLM writes `.py` files via a tool and habitually indents top-level statements inside triple-quoted strings (imports at column 0, body one block deep). Where do you validate, what do you auto-repair, and what must still fail?

## Write-path validation ladder
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/filesystem/workspace_fs.py` (`write_file` :184-194; `_normalize_python_script_content` :130-140; `_peel_agent_block_indent` :116-127; `_validate_python_script` :143-159; `_is_python_script_path` :90-91).
**Signature:** `write_file(path: str, content: str) -> str`; helpers: `_normalize_python_script_content(content) -> str`, `_peel_agent_block_indent(content) -> str`, `_validate_python_script(content, path) -> str | None`.
**Data Shape:** Validation fires ONLY on `path.suffix.lower() == ".py"` (checked after backslash→slash normalization); non-`.py` writes skip it entirely. Errors return as `[write_file error] ...` strings — never exceptions into the agent.

### Decisive source
```python
# workspace_fs.py:130-140 — repair BEFORE validate, and only if needed
def _normalize_python_script_content(content: str) -> str:
    content = textwrap.dedent(content).lstrip("\n")   # all-lines-indented case
    if _python_compiles(content):
        return content                                 # already valid → untouched
    return _peel_agent_block_indent(content)           # structural peel, then re-validate

# :116-127 — peel ONLY when imports sit at col 0 and later lines are indented
non_blank = [(i, _line_indent(ln)) for i, ln in enumerate(lines) if ln.strip()]
if not non_blank or non_blank[0][1] != 0: return content
later_indents = [ind for _, ind in non_blank[1:] if ind > 0]
if not later_indents: return content
block = min(later_indents)   # peel exactly ONE level = min indent of body

# :143-158 — error names the line + quotes it + adds guidance only for "unexpected indent"
```

**Flow:** suffix check → `textwrap.dedent` → compile-probe → if still failing AND first non-blank line is column 0 with a uniform positive min-indent below, strip exactly that block from every line ≥ it (`_strip_block_indent`) preserving trailing newline → final `compile()`; SyntaxError message includes `line N`, the offending source line, and an extra hint only when `exc.msg` contains "unexpected indent" ("do not indent lines inside \"\"\"...\"\"\""). Failure returns before ANY backend write.
**Invariant:** The peel must run BEFORE validation but must never mask a real syntax error AS "unexpected indent" — a genuinely broken statement inside an indented script must report its true error (`event_start` in the test) after the peel. Valid nested indentation (function bodies under column-0 defs) is preserved because dedent is a no-op when common leading whitespace is 0 and the peel only triggers when imports are at column 0 while ALL other non-blank lines are indented.
**Probe:** direct tests `cuga_lite/executors/filesystem/tests/test_workspace_fs.py::test_write_file_auto_dedents_uniform_indent` (:287), `::test_write_file_auto_dedents_imports_plus_block_indent` (:298), `::test_write_file_reports_real_syntax_error_after_block_peel` (:329 asserts `"unexpected indent" not in msg`), `::test_write_file_peels_block_indent_even_when_script_has_syntax_error` (:345), `::test_write_file_preserves_valid_nested_indentation` (:360), `::test_write_file_rejects_invalid_python_after_dedent` (:381), `::test_write_file_python_validation_does_not_overwrite_existing` (:394), `::test_write_file_skips_python_validation_for_non_py` (:408).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "WorkspaceFilesystem write_file _normalize_python_script_content _peel_agent_block_indent", limit: 10 });
```

## Verdict
Adopt the ladder order (dedent → compile → structural peel → compile → write-or-error-string), the "first line col-0 + min-body-indent" trigger, and the failed-write-leaves-old-file-intact rule. Adapt the error-message wording/hint to your tool's voice. Omit nothing from the ordering: validating before normalizing produces false rejects (the exact bug this ladder exists for).
