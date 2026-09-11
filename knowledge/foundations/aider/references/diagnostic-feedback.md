<!-- capsule-v2 -->
# Diagnostic feedback — preserve failing output and scope source to reported lines

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How can an agent loop turn post-edit diagnostics into a bounded, actionable repair message without dropping the failed tool output or flooding the model with a whole file?

## Lint result assembly
**Path/Symbol:** `aider/linter.py`: `Linter.run_cmd` (:47-68), `errors_to_lint_result` (:70-80), `lint` (:82-116); `aider/coders/base_coder.py`: `Coder.lint_edited` (:1681).
**Signature:** `Linter.lint(fname, cmd=None) -> str | None`; `Coder.lint_edited(fnames) -> str`.
**Data Shape:** relative target filename, merged command output, zero-based reported diagnostic lines, `LintResult(text, lines)`, and a tree-shaped local structural excerpt.

### Decisive source
```python
if returncode == 0:
    return
res = f"## Running: {cmd}\n\n" + errors
return self.errors_to_lint_result(rel_fname, res)
...
res = "# Fix any errors below, if possible.\n\n"
res += lintres.text
res += "\n" + tree_context(rel_fname, code, lintres.lines)
return res
```

**Flow:** select a project, language, or basic lint command; quote the relative target path; on a nonzero result preserve the command plus merged output; extract reported line numbers; append only the structural context around those lines; concatenate results for edited files and surface one warning so the model can respond to a repair message.

**Invariant:** success produces no feedback. Failure preserves the original diagnostic text and scopes source context to reported lines, so the model receives evidence instead of an opaque failure or an unbounded file dump.

**Probe:** `tests/basic/test_linter.py::test_run_cmd_with_errors` (:51) asserts nonzero output becomes a `LintResult`; `test_run_cmd_with_special_chars` (:61) verifies a special-character file path survives command construction. The direct test command is blocked in this clone because `pytest` is not installed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "Linter lint errors_to_lint_result lint_edited tree_context", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt diagnostic-text preservation plus line-scoped structural context as the repair payload; adapt command execution and syntax-tree helpers; omit Aider's Python/flake8 defaults.
