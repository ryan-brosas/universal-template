<!-- capsule-v2 -->
# Code-validation kernel — which lint/parse checks run per extension, and what does "worse than baseline" precisely compare?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** The apply loop (fcr-application-loop) and pre-validation (fcr-prevalidation-plane) both depend on a baseline-relative lint/parse oracle — what exactly runs per file extension, and how is "the edit made things worse" computed from two raw lint outputs?

## get_check_results: syntax-first ladder, pylint for .py, eslint probe for js/ts, everything else empty
**Path/Symbol:** `sweepai/utils/code_validators.py:get_check_results` (:498–545), `check_syntax` (:352–407), `get_pylint_check_results` (:469–496), `CheckResults` (:255–292), `is_worse_than` (:262–267), `is_worse_than_message` (:269–292), `get_new_lint_errors_for_pylint` (:217–235), `get_new_lint_errors_for_eslint` (:238–251), `DEFAULT_ESLINTRC` (:410), `pylint_args_non_last_fcr`/`pylint_args_last_fcr` (:449/:459). **Consumers:** `sweepai/agents/modify_utils.py:1008` (baseline capture into `llm_state['initial_check_results']`) and `:1150–1152` (per-edit re-check + message feed into the next tool call); `chunk_code` in this same file (:601) is the shared chunking kernel consumed by repo_parsing_utils.py:102 and annotate_code_openai.py:98 (covered by repo-parsing-chunk-plane / snippet-annotation-plane).

**Signature:** `get_check_results(file_path: str, code: str, last_fcr_for_file=False) -> CheckResults`; `CheckResults.is_worse_than_message(other: CheckResults) -> str` (empty string == "not worse").
**Data Shape:** `CheckResults` is a dataclass of three RAW TEXT fields — `parse_error_message`, `pylint`, `eslint` — no structured error objects; all comparison is line-count + fuzzy text diff over those strings.

### Decisive source
```python
def get_check_results(file_path: str, code: str, last_fcr_for_file=False) -> CheckResults:
    is_valid, error_message = check_syntax(file_path, code)
    if not is_valid:
        return CheckResults(parse_error_message=error_message)
    ext = file_path.rsplit(".")[-1] # noqa
    if ext == "py":
        try:
            return get_pylint_check_results(file_path, code, last_fcr_for_file=last_fcr_for_file)
        except Exception as e:
            logger.exception(e)
    elif ext in ["js", "jsx", "ts", "tsx"]:
        # see if eslint is installed
        npx_commands = ["npx", "eslint", "--version"]
        try:
            result = subprocess.run(" ".join(npx_commands), timeout=5, ...)
        except subprocess.TimeoutExpired:
            raise Exception("ESLint timed out after 5s. You need eslint to edit js/ts files. Run `npm i -g eslint ...`.")
        ...  # timeout=30 run; TimeoutExpired ⇒ logger.warning + fall through
    return CheckResults()

# baseline-relative comparison (modify_utils.py):
llm_state['initial_check_results'][file_name] = get_check_results(file_name, get_latest_contents(...))   # :1008, BEFORE applying
check_results = get_check_results(file_name, new_file_contents, last_fcr_for_file=is_last_fcr_for_file)  # :1150, AFTER each make_change
check_results_message = check_results.is_worse_than_message(llm_state['initial_check_results'][file_name])  # :1151
failing_parse = check_results.parse_error_message if not llm_state['initial_check_results'][file_name].parse_error_message else ""  # :1152

# "new errors" = fuzzy additions filtered by type frequency:
additional_errors = patience_fuzzy_additions(old_errors, new_errors).splitlines()
if error_type.startswith("E") or old_error_types.count(error_type) < 2:  # if there are more than 1 of the same error, we consider it new
    results.append(line)
```

**Flow:** get_check_results is a strict ladder: check_syntax FIRST for every extension in the `extension_to_language` table (tree-sitter parse; python additionally gets an `ast.parse` fast path that produces a friendlier "Python syntax error: {msg} at line {lineno}"; unsupported extensions return `(True, "Unsupported file extension, skipping syntax check.")` — they are VALID by default); a syntax failure short-circuits to `CheckResults(parse_error_message=...)` and no linter ever runs → `.py` ⇒ get_pylint_check_results under `@file_cache`: writes `/tmp/{uuid}_{basename}`, runs pylint `Run` with a TextReporter, strips everything after the first `----` header line, rewrites the temp path back to the real path, prefixes `> pylint {file_path}`; ANY exception is logged and falls through to an EMPTY CheckResults (a crashed linter means "no problem") → js/jsx/ts/tsx ⇒ availability probe `npx eslint --version` with timeout=5 — TimeoutExpired RAISES an Exception carrying npm install instructions (the only hard failure in the whole ladder); if available, runs in a `TemporaryDirectory(dir=os.getcwd())` with the baked-in DEFAULT_ESLINTRC (typescript-eslint parser, react plugin, no-undef/no-unused-vars/import-first as errors) at timeout=30 — TimeoutExpired here only warns and yields EMPTY results → any other extension ⇒ empty CheckResults. The two pylint arg sets differ in exactly one rule: the LAST fcr-for-file enables W0611 (unused import), earlier ones disable it — so unused-import noise is only charged on the final state of each file.
**Invariant:** Validation is RELATIVE to the pre-edit baseline, never absolute cleanliness: `is_worse_than_message(baseline)` returns "" when the baseline already had a parse error (a broken file cannot get worse), when the line count did not grow, or when every "new" line is an error type that already appeared twice in the old output (frequency ≥2 ⇒ pre-existing, suppressed); pylint E-prefix (error-severity) lines are ALWAYS reported as new regardless of frequency; eslint skips "✖" summary lines. The boolean twin `is_worse_than` has ZERO production callers at pin — only the message form feeds the repair loop, so the model sees human-readable deltas, not booleans. Linter crashes degrade to "no problem" everywhere EXCEPT the eslint availability probe, which hard-fails js/ts edits with install instructions.
**Probe:** No offline-runnable test passes at pin: `sweepai/utils/utils_test.py` (pytest, 3 parametrized cases for check_syntax) EXISTS but EXECUTED `python3 -m unittest sweepai.utils.utils_test -v` → FAILED at import (ModuleNotFoundError: pylint), and its expected message "Invalid syntax found within or before the lines 0-0" does not match the current source format ("Invalid syntax found from {start}-{end}" / "at line {n}") — STALE even if the import were fixed. Deterministic probes executed at pin: `grep -n 'def get_check_results\|def check_syntax\|def get_pylint_check_results\|class CheckResults\|def is_worse_than' sweepai/utils/code_validators.py` → :255,:262,:269,:299,:352,:469,:498; `grep -n 'W0611' sweepai/utils/code_validators.py` → :452,:462 (one per arg set); `grep -n 'timeout=5\|timeout=30' sweepai/utils/code_validators.py` → :514,:538; `grep -rn 'get_check_results(' sweepai --include=*.py | grep -v def` → modify_utils.py:1008,:1150 + __main__ demo rows :784/:792/:793/:795; `grep -rn 'is_worse_than' sweepai --include=*.py` → defs :262/:269 + sole production use modify_utils.py:1151 (message form only); `grep -rn 'check_valid_typescript' sweepai --include=*.py` → :299 def + :371 comment reference only (DEAD — the ts branch in check_syntax is commented out); `grep -rn 'naive_chunker\|chunk_tree' sweepai --include=*.py` → :201/:616 and :93/:631 (both live inside chunk_code's known-language vs fallback paths).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "get_check_results is_worse_than_message patience_fuzzy_additions initial_check_results", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// code_validators.py :217-296/:352-407/:449-545 + modify_utils.py :1008/:1150-1152 at pin
// substituted — see verification.md pass 7.
```

## Verdict
Adopt the baseline-relative comparison (capture check results BEFORE the first edit, compare line counts AFTER each edit, report only NEW errors to the model — absolute cleanliness gates would make the loop fail on legacy codebases), the frequency≥2 pre-existing-type suppression (cheap way to ignore errors the model did not introduce), the parse-error-cannot-get-worse rule, and the crash-degrades-to-empty posture for optional linters. Adapt: the raw-text dataclass is fragile (line counts as severity proxy, space-splitting of lint output formats) — keep the shape but pin the linter version you parse; the single-rule delta between last/non-last FCR arg sets is a nice cheap trick worth copying; the eslint availability probe raising with install instructions is the right asymmetry (hard-fail when you cannot validate at all, soft-fail when validation times out). Omit: check_valid_typescript (dead at pin), the /tmp uuid-file pylint dance (use pylint's in-memory input if your host allows), and the boolean is_worse_than (no callers). Coverage caveat: utils_test.py is stale AND import-blocked (pylint absent) — recorded as runner block, not a pass; five production touch points (baseline capture + per-edit re-check in the apply loop) mean behavior changes here alter every apply loop's repair quality.
