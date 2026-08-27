<!-- capsule-v2 -->
# FCR pre-validation plane — how do you pre-validate parsed change requests against the repo before entering the LLM repair loop?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** Before any apply-loop or repair-loop LLM call is spent, how does Sweep decide which parsed FileChangeRequests are structurally broken, what exact error text each breakage gets, and how do sequential edits to overlapping regions avoid false positives?

## set_fcr_change_type + get_error_message_formatted: change-type flipping, suffix-match rescue, drop markers, previous-FCR escape hatches, tokenized fuzzy did-you-mean
**Path/Symbol:** `sweepai/agents/modify_utils.py:set_fcr_change_type` (:1232–1249), `validate_file_path` (:1255–1270), `get_error_message_formatted` (:1271–1426), `get_error_message_dict` (:1428–1430), `get_error_message` (:1432–1433). **Consumers:** planner repair loops at `sweepai/core/sweep_bot.py:646/:692` (live ticket), `:963/:1008` (context variant), `:1509/:1545` (GHA variant + its per-round re-validation); chat-plane annotations at `sweepai/chat/api.py:752`.
**Signature:** `get_error_message_formatted(file_change_requests, cloned_repo, updated_files={}, renames_dict={}) -> (list[str], list[int])` (error messages + their FCR indices); `set_fcr_change_type(fcrs, cloned_repo, renames_dict={}) -> None` (mutates change_type in place).
**Data Shape:** input = parsed FCR list (filename, instructions with `<original_code>`/`<new_code>` blocks, change_type) + repo on disk; output = parallel (message, index) pairs where index addresses the FCR list — the repair loop's `<fix index>`/`<drop index>` grammar is built on these indices.

### Decisive source
```python
def set_fcr_change_type(file_change_requests, cloned_repo, renames_dict={}):
    reverse_renames = {v: k for k, v in renames_dict.items()}
    for fcr in file_change_requests:
        if fcr.change_type == "modify":
            try: get_file_contents(fcr.filename)
            except FileNotFoundError: fcr.change_type = "create"      # file missing ⇒ it's a creation
        elif fcr.change_type == "create":
            try: cloned_repo.get_file_contents(fcr.filename)
                fcr.change_type = "modify"                            # file exists ⇒ it's an edit
            except FileNotFoundError: pass
...
# get_error_message_formatted, modify branch:
except FileNotFoundError as e:
    for file_path in cloned_repo.get_file_list():
        if file_path.endswith(file_change_request.filename):          # SUFFIX-MATCH RESCUE: rebind filename
            file_contents = get_file_contents(file_path)
            file_change_request.filename = file_path
    else:
        ... error "The file `{...}` does not exist. Double-check your spelling."  (only if original_code present)
        ... else flip to create + validate_file_path
...
# presence check with TWO escape hatches for sequential edits:
original_code_in_previous_fcr = any(contains_ignoring_whitespace(original_code, fcr["new_code"][0]) for fcr in previous_parsed_fcrs[:-1])
previous_fcr_occurrences = [contains_ignoring_whitespace(fcr["new_code"][0], original_code) for fcr in previous_parsed_fcrs[:-1]]
all_previous_occurrences = [x[1] - x[0] if x else 0 for x in previous_fcr_occurrences]
if all_previous_occurrences and max(all_previous_occurrences) > len(original_code.splitlines()) // 2:
    previous_fcr_in_original_code = True                              # prior edit covers >50% of this block ⇒ legal
if not contains_ignoring_whitespace(original_code, file_contents) and not original_code_in_previous_fcr and not previous_fcr_in_original_code:
    best_match, current_best_score = find_best_match(original_code, file_contents, threshold=threshold, tokenized=True)   # :1354
    for indent_count in range(0, max_indentation(file_contents), 2):  # best-indent re-search over FILE's max indent
        match_score = fuzz.ratio(indent(original_code, indent_count), best_match)
    ...
    if not check_valid_parentheses(best_match):                       # extend to a parenthesis-balanced span
        extended_match = find_smallest_valid_superspan(best_match, file_contents)
        if extended_match and extended_match.count("\n") - best_match.count('\n') < 20: best_match = extended_match
    if best_score > 80: ... did-you-mean diff n=10 ... else find_best_matches plural listing
    # appended hints: too_long_message (>50 lines) + ellipses_message ("# ..." or "// ..." present)
...
# parenthesis-mismatch check ONLY for brace languages:
if ext.removeprefix(".") in ["java", "c", "cpp", "h", "hpp", "js", "ts", "jsx", "tsx", "go", "rs"]:   # :1391
```

**Flow:** set_fcr_change_type runs FIRST and flips change types against disk truth (modify→create when the file is absent via reverse-renames lookup; create→modify when present) so downstream validation uses the right branch → per-FCR ladder for modify: FileNotFoundError triggers a suffix-match RESCUE (any repo file whose path endswith the given name rebinds the FCR's filename — tolerates the model dropping directory prefixes); no rescue AND original_code present ⇒ "file does not exist" error; no original_code ⇒ silently flip to create and validate the path instead → structural checks: missing `<original_code>` or `<new_code>` block ⇒ error offering `<drop>{i}</drop>` as the escape valve; original == new ⇒ error; empty original ⇒ an explicit append recipe (copy anchor into both blocks, append after) → presence check via contains_ignoring_whitespace with two escape hatches that make SEQUENTIAL EDITS legal: the original_code may already be inside a PREVIOUS fcr's new_code, or a previous fcr's new_code may cover more than half of this original_code's lines (the edits will compose once applied in order) → only then fuzzy search: find_best_match with tokenized=True (comment/blank lines stripped, stringzilla token split) at threshold=50, plus a best-indent re-search bounded by the FILE's own max indentation; empty best_match ⇒ "now where to be found"; score ≠ 100 ⇒ if the best match itself has unbalanced parentheses, extend it to the smallest balanced superspan (only when <20 extra lines) before diffing; >80 ⇒ single did-you-mean with diff n=10; else a plural "one of the following" listing from find_best_matches → two always-appended hints when relevant: the block is >50 lines (isolate it) and/or it contains "# ..."/"// ..." ellipses (copy code in full) → for brace languages only, a parenthesis-balance comparison between original and new code catches would-be syntax errors pre-apply, suggesting the superspan fix when new_code is itself balanced → create branch: validate_file_path (file exists ⇒ modify-or-drop hint naming the `<drop>{i}</drop>` marker; directory is a file; similar-directories suggestion from cloned_repo.get_similar_directories).
**Invariant:** Validation is PURE with respect to the repo state except for the two in-place mutations it owns: change_type flips and the suffix-match filename rebind — both move the FCR toward disk truth, never away. The index space is the contract: every error message carries its position in the FCR list, and the repair prompt's allowed_indices/drop grammar (see llm-plan-continuation-and-repair) consumes exactly these indices; a port that changes the addressing must change both sides together. The >50%-coverage escape hatch encodes the domain fact that multi-edit plans are ORDERED: later edits reference the post-earlier-edit text, so "not found yet" is not an error when a preceding edit explains it. Ellipsis detection ("# ..."/"// ...") is a cheap proxy for the model's most damaging habit — abbreviating code it was told to copy verbatim.
**Probe:** No offline-runnable test covers this plane at pin (same import block as search-replace-match-ladder: rapidfuzz/stringzilla/anthropic chain). Deterministic probes executed at pin: `grep -n 'def set_fcr_change_type\|def validate_file_path\|def get_error_message_formatted\|def get_error_message_dict\|def get_error_message' sweepai/agents/modify_utils.py` → :1232,:1255,:1271,:1428,:1432; `grep -n 'threshold = 50' sweepai/agents/modify_utils.py` → :1353 only; `grep -n 'tokenized=True' sweepai/agents/modify_utils.py` → :1354,:1380; `grep -n 'removeprefix(".") in \[' sweepai/agents/modify_utils.py` → :1391 only; `grep -n 'endswith(file_change_request.filename)' sweepai/agents/modify_utils.py` → 1 row (rescue loop); `grep -n 'splitlines()) // 2' sweepai/agents/modify_utils.py` → 1 row (>50% rule); `grep -n 'get_error_message(' sweepai/core/sweep_bot.py` → :646,:692,:963,:1008,:1509,:1545 (repair loops; :1545 is the GHA loop's per-round re-validation); `grep -n 'get_error_message_dict(' sweepai/chat/api.py` → :752 only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "set_fcr_change_type get_error_message_formatted validate_file_path find_smallest_valid_superspan drop marker", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// modify_utils.py :1232-1433 at pin substituted — see verification.md pass 6.
```

## Verdict
Adopt the pre-validation-before-LLM-repair ordering (cheap disk-truth checks and structural checks first, fuzzy did-you-mean last — every LLM repair round costs a full model call), the index-addressed error contract shared with the repair loop, the ordered-plan escape hatches (previous-fcr containment and >50% coverage) that make sequential edits validatable without simulating them, and the language-gated parenthesis check (brace languages only — Python's indentation makes bracket counting noise). Adapt: the suffix-match rescue is aggressive (any path ending in the name wins) — scope it to the same directory depth or rank by similarity; the brace-language list is a closed heuristic table; the <drop> marker grammar should be whatever your repair prompt already speaks. Omit: the commented-out `<error index=...>` XML assembly (the flat (messages, indices) pair is the real contract), the "todo: integrate this into the main function" fragmentation, and the duplicated create-path validation between the flip branch and the create branch. Coverage caveat: no live direct test at pin (import-blocked module); five production call sites mean a behavior change here alters every planner's repair quality.
