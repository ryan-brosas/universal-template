<!-- capsule-v2 -->
# Linter language dispatch — routing per-language checks and merging heterogeneous diagnostics

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you route linting per language (callable vs shell command vs generic parser) and fuse multiple diagnostics into ONE bounded repair payload? *(Companion to diagnostic-feedback.md, which covers result assembly and tree context.)*

## Four-rung dispatch + Python three-way merge (tree-sitter, compile(), fatal flake8)
**Path/Symbol:** `aider/linter.py`: `Linter.lint(fname, cmd=None)` (:82-116), `set_linter(lang, cmd)` (:31-36), `py_lint` (:118-134), `lint_python_compile` (:177-198), `basic_lint` (:201-231), `flake8_lint` (:136-168).
**Signature:** `lint(fname, cmd=None) -> str | None`; `languages: dict[lang, str|callable]`; falsy lang in set_linter sets the global `all_lint_cmd`.
**Data Shape:** `LintResult(text, lines)` merged by newline-joined text and UNIONED line numbers; python seeded at init: `languages=dict(python=self.py_lint)`.

### Decisive source
```python
lang = filename_to_lang(fname)
if not lang: return
if self.all_lint_cmd: cmd = self.all_lint_cmd
else: cmd = self.languages.get(lang)

if callable(cmd):   lintres = cmd(fname, rel_fname, code)     # in-process checker
elif cmd:           lintres = self.run_cmd(cmd, rel_fname, code)  # shell command
else:               lintres = basic_lint(rel_fname, code)     # tree-sitter fallback
...
def py_lint(self, fname, rel_fname, code):
    basic_res = basic_lint(rel_fname, code)          # ERROR/is_missing nodes
    compile_res = lint_python_compile(fname, code)   # SyntaxError lineno..end_lineno
    flake_res = self.flake8_lint(rel_fname)          # --select=E9,F821,F823,F831,F406,F407,F701,F702,F704,F706
    text = ""; lines = set()
    for res in [basic_res, compile_res, flake_res]:
        if not res: continue
        if text: text += "\n"
        text += res.text; lines.update(res.lines)
    if text or lines: return LintResult(text, lines)
```

**Flow:** explicit cmd arg > global all_lint_cmd > per-language table entry > tree-sitter basic_lint -> table entries may be callables (invoked in-process with (fname, rel_fname, code)) or strings (shell-executed with oslex-quoted target) -> Python merges three sources into one LintResult (union of zero-based lines) -> diagnostic-feedback's assembly wraps text + TreeContext excerpt.
**Invariant:** compile()'s traceback is truncated at the "# USE TRACEBACK BELOW HERE" marker comment (:179/:188-195) keeping header line + post-marker frames only — the reported line range spans `err.lineno-1 .. end_lineno`; TypeScript is excluded from tree-sitter parsing entirely (#1132, :210-212); a RecursionError in traversal disables the tree-sitter rung for that file instead of crashing.
**Probe:** `tests/basic/test_linter.py` — `test_init` (:13), `test_set_linter` (:18), `test_get_rel_fname` (:22), plus the run_cmd family (:31-68). Executed GREEN this run (repo `.venv`, suite: 30 passed, 1 skipped across the three-file batch). Anchors: `grep -nF 'USE TRACEBACK BELOW HERE' aider/linter.py` -> :179; `grep -nF '--select={fatal}' aider/linter.py` -> :142; `grep -nF 'self.languages.get(lang)' aider/linter.py` -> :99.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "py_lint", limit: 3 });
// resolves Linter.py_lint :118-134 rank-1
```

## Verdict
Adopt the four-rung dispatch with callable/string duality and union-merge of parallel diagnostics. Adapt tool choices and the fatal-only select list to the host; omit Aider's grep_ast dependency only if you supply equivalent tree-sitter bindings. Do not widen flake8's select beyond fatal codes — style noise drowns the repair signal.
