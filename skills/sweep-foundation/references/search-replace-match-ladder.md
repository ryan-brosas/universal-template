<!-- capsule-v2 -->
# Search-and-replace match ladder — how do you match an LLM-provided original_code against real file contents and turn every mismatch into an actionable repair prompt?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** The apply loop's make_change tool receives an original_code string that may be mis-indented, rstripped, CRLF-poisoned, duplicated, already applied, or in the wrong file — what is the ordered ladder of checks that either applies the edit or produces an error message good enough for the model to self-correct?

## handle_function_call make_change path: indent search → already-applied → did-you-mean (same file, then cross-file) → uniqueness → apply → baseline-relative validation
**Path/Symbol:** `sweepai/agents/modify_utils.py:handle_function_call` (:980–1230, make_change branch :1000–1229), fuzzy kernels `find_best_matches` (:502–571), `find_best_match` (:571–573), `contains_ignoring_whitespace` (:609–620), `find_smallest_valid_superspan` (:583–607), `get_surrounding_lines` (:842–864), `tokenize_code` (:456–469); `sweepai/utils/ripgrep_utils.py:manual_code_check` (:66–113); `sweepai/utils/code_validators.py:get_check_results` (:498+).
**Signature:** `handle_function_call(cloned_repo, function_call, modify_files_dict, llm_state, chat_logger_messages=None, use_openai=False) -> tuple[str, dict]`; `find_best_matches(needle, haystack, threshold=50, verbose=True, num_matches=5, tokenized=False) -> list[(str, score)]`; `manual_code_check(file_contents, code_snippet) -> tuple[int, bool]` (indent spaces, rstrip-needed; (-1, False) on miss).
**Data Shape:** input = tool-call dict {file_name, original_code, new_code, replace_all?} + latest file contents; output = ERROR/SUCCESS/DONE/SKIPPED response string + mutated modify_files_dict + llm_state.

### Decisive source
```python
# handle_function_call, make_change branch — wrapped in `for _ in range(1):  # this is super jank code but it works for now` (:1000)
if "\r\n" in file_contents:                       # :1020 — CRLF makes search-and-replace ALWAYS fail
    file_contents = file_contents.replace("\r\n", "\n")
correct_indent, rstrip_original_code = manual_code_check(file_contents, original_code)   # :1024
if original_code not in file_contents and correct_indent == -1:
    if new_code.strip() and contains_ignoring_whitespace(new_code, file_contents):        # :1027
        error_message = "Your original_code was not found in the file but your new_code was found. This is likely because this fix has already been applied. ... call the submit_task tool."
    best_match, best_score = find_best_match(original_code, file_contents)                # :1031
    if best_score > 80:                                                                    # :1032
        surrounding_lines_before, surrounding_lines_after = get_surrounding_lines(file_contents, best_match)
        for indentation in range(0, 10):                                                  # best-indent re-search
            score = rapidfuzz.fuzz.ratio(indent(original_code, indentation), best_match)
        ...
        error_message = f"...Did you mean the following?\n```\n{best_match}\n```...{best_match_diff}\n```" + DID_YOU_MEAN_PROMPT
    else:                                                                                  # CROSS-FILE scan over other FCR files
        all_file_contents = list(dict.fromkeys([get_latest_contents(fcr.filename, ...) for fcr in llm_state["fcrs"] if fcr.filename != file_name]))
        ...
        if best_score > 80: ... "The code was found in {other_file_name}. Call make_changes again with the correct file name."
    # else ORIGINAL_CODE_NOT_FOUND_PROMPT
original_code, new_code, original_code_lines = validate_indents(original_code, new_code, file_contents, correct_indent, rstrip_original_code)
current_chunk_occurences = file_contents.count(original_code)                              # :1080
if current_chunk_occurences > 1 and not replace_all:
    if current_chunk_occurences * len(original_code.split("\n")) < 50:                    # enumerate occurrences w/ ±10 lines context
        ...
new_file_contents = file_contents.replace(original_code, new_code, 1)                     # :1140 (or .replace(...) when replace_all)
check_results_message = check_results.is_worse_than_message(llm_state['initial_check_results'][file_name])   # :1151 — BASELINE-relative
...
if llm_state["attempt_count"] > 5:                                                        # :1185 — force-skip the task
    ... fcr.is_completed = True ... llm_response = f"SKIPPED\n\nThe previous task took too many attempts so we gave up. ..."
```

**Flow:** missing-key check first (a missing new_code/original_code gets the "WAY TOO LARGE … REDUCE the original_code block to be under 10 lines" hint — the model's most common failure mode is oversized blocks that swallow the closing tags) → file must exist on disk or already be in modify_files_dict → a BASELINE lint/parse snapshot (`initial_check_results[file]`) is taken before any edit so later validation is relative, not absolute → CRLF is normalized away in the working copy (Windows repos would otherwise fail every replace) → manual_code_check searches the snippet at every 2-space indent level (0..38) plus an rstripped variant, returning the winning indent or -1 → if still absent: the new_code-present check catches ALREADY-APPLIED edits (idempotency by content, telling the model to submit_task); else find_best_match (fuzzy sliding-window, threshold 50) scores the closest real span — >80 ⇒ a did-you-mean error embedding the actual code, ±surrounding lines (6 before / 12 after via get_surrounding_lines), a best-indent re-search over 0..9, and a bounded diff (n=20); ≤80 ⇒ the same search runs across the OTHER FCR files' contents (wrong-file detection, diff n=14); else the generic not-found prompt → validate_indents re-indents new_code to the found indent and, for multi-line rstrip matches, re-reads the ACTUAL byte span from the file (the model's whitespace is never trusted for the replacement anchor) → uniqueness gate: count > 1 without replace_all ⇒ if total occurrence size < 50 lines, every occurrence is enumerated with ±10 surrounding lines as "Occurrence N:" blocks (teaching the model how to disambiguate); else a plain non-unique error → apply via str.replace(..., 1) (or unbounded for replace_all); a no-op replace is itself an error → post-edit get_check_results is compared to the baseline with is_worse_than_message: NEW parse errors produce a parentheses-diff diagnosis (which bracket type, how many extra) or a generic syntax-fix prompt; new warnings produce linter prompts (an indentation-specific variant when the edit changed indentation depth) → every error increments attempt_count and disables lazy application; >5 errors force-completes the FCR with a SKIPPED message so one bad task cannot consume the whole budget.
**Invariant:** Every failure mode maps to a DISTINCT, self-correcting error message — the contract is "the model can fix its own next call from the error text alone": already-applied ⇒ submit_task; near-miss ⇒ here-is-the-real-code-plus-diff; wrong file ⇒ here-is-the-right-file; duplicate ⇒ here-are-all-occurrences-with-context; broken syntax ⇒ here-is-the-bracket-arithmetic. Matching is whitespace-tolerant BY CONSTRUCTION (indent ladder + rstrip variants + contains_ignoring_whitespace) because LLM output whitespace is unreliable, but the replacement anchor is always re-derived from the FILE's bytes, never the model's. Validation is baseline-relative: pre-existing lint debt in the file must not block the edit, only NEW breakage does. The whole ladder terminates because each rung either applies, emits a distinct error (bounded by attempt_count), or skips the task.
**Probe:** tests/test_modify_utils.py (153L, 7 tests incl. handle_submit_task with MagicMock fcrs) EXISTS for this module but is IMPORT-BLOCKED at pin: executed `python3 -m unittest tests.test_modify_utils -v` → FAILED (errors=1), ModuleNotFoundError: No module named 'rapidfuzz' (chain also needs stringzilla, loguru, tqdm, anthropic/openai/parea via sweepai.core.chat). Deterministic probes executed at pin: `grep -n 'for _ in range(1)' sweepai/agents/modify_utils.py` → :1000 only; `grep -n 'in file_contents:' sweepai/agents/modify_utils.py | grep '\\r\\n'` → :1020; `grep -n 'already been applied' sweepai/agents/modify_utils.py` → :1028 only; `grep -n 'best_score > 80' sweepai/agents/modify_utils.py` → :1032,:1057 (make_change same-file + cross-file) + :1377 (pre-validation plane's own did-you-mean gate, see fcr-prevalidation-plane); `grep -n 'current_chunk_occurences' sweepai/agents/modify_utils.py` → :1080,:1081,:1082,:1100,:1119,:1121; `grep -n 'replace(original_code, new_code, 1)' sweepai/agents/modify_utils.py` → :1140 only; `grep -n 'attempt_count"\] > 5' sweepai/agents/modify_utils.py` → :1185 only; `grep -n 'def manual_code_check' sweepai/utils/ripgrep_utils.py` → :66; `grep -rn 'sliding_window_replacement' sweepai/ tests/` → diff.py:182 (def) + diff.py:469 (__main__ demo) ONLY — zero production callers at pin; `grep -n 'NUM_LINES_SURROUNDING' sweepai/agents/modify_utils.py` → :850 (=6),:851,:856.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "find_best_matches contains_ignoring_whitespace manual_code_check get_surrounding_lines DID_YOU_MEAN_PROMPT MULTIPLE_OCCURRENCES_PROMPT", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// modify_utils.py :456-620/:842-1230 and ripgrep_utils.py:66-113 at pin substituted — see verification.md pass 6.
```

## Verdict
Adopt the ordered mismatch ladder as a pattern: cheap exact/whitespace-tolerant checks first (indent ladder, rstrip variants), idempotency check (new_code present ⇒ already done) BEFORE fuzzy search, fuzzy did-you-mean with the REAL code embedded plus a bounded diff, cross-file wrong-target detection, occurrence enumeration with context for duplicates, and baseline-relative post-edit validation. Adopt the "every error teaches the next call" contract and the attempt-count force-skip so one bad task cannot burn the budget. Adapt: the thresholds (score > 80, threshold=50, <50-line enumeration cap, ±10 context lines, 0..9 indent re-search) are tuned heuristics — measure your own model's failure distribution; the `for _ in range(1)` break-based control flow is explicitly marked jank and should become real functions in a port; rapidfuzz QRatio over tokenized text is the right scorer for code but requires the dependency. Omit: the stdout prints, the TODO-laden inline comments-as-spec, and sliding_window_replacement (diff.py:182) which has zero production callers at pin. Coverage caveat: the module's own unit test file exists but is import-blocked offline (rapidfuzz absent); no behavioral test evidence at pin — the ladder's correctness rests on source reading plus the live e2e harnesses that need GITHUB_PAT.
