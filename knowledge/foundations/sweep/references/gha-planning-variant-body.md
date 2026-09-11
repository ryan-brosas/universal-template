<!-- capsule-v2 -->
# GHA planning variant body — how does the GitHub-Actions autofix planner differ from the live ticket planner (two-stage reflection→plan ladder over post-change code)?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** When a bot PR's CI fails, the autofix path re-plans over files that ALREADY carry the first attempt's edits — what is the two-stage prompt ladder, which shared kernels does it reuse, and where does it diverge from the live ticket planner?

## get_files_to_change_for_gha: content swap → shared budget kernel → reflection stage → system-prompt swap → plan stage → ≤3 repair rounds
**Path/Symbol:** `sweepai/core/sweep_bot.py:get_files_to_change_for_gha` (:1360–1554); prompts `gha_files_to_change_system_prompt` (prompts.py:368), `gha_files_to_change_system_prompt_2` (:377), `gha_files_to_change_prompt` (:392), `gha_files_to_change_prompt_2` (:426), `GHA_PROMPT` (sweep_bot.py:89), `GHA_PROMPT_WITH_HISTORY` (:108); `cleanup_fcrs` (sweep_bot.py:132); call sites `sweepai/handlers/on_failing_github_actions.py:159–183` (first pass) and `:344–367` (retry with history).
**Signature:** `get_files_to_change_for_gha(relevant_snippets, read_only_snippets, problem_statement, updated_files, cloned_repo, pr_diffs="", chat_logger=None, use_faster_model=False, use_openai=False) -> tuple[list[FileChangeRequest], str]`.
**Data Shape:** input = snippets + the FIRST attempt's modify_files_dict (post-change contents); output = FCR list (each stamped raw_relevant_files) + the raw plan text; degenerate shape = ([], "") on RegexMatchError.

### Decisive source
```python
for relevant_snippet in relevant_snippets:                       # :1377 — CONTENT SWAP: planner sees POST-change code
    if relevant_snippet.file_path in updated_files:
        relevant_snippet.content = updated_files[relevant_snippet.file_path]["contents"]
...
max_snippets = get_max_snippets(interleaved_snippets)            # :1392 — SHARED budget kernel (see llm-file-selection-budget-plane)
...
MODEL = "claude-3-opus-20240229" if not use_faster_model else "claude-3-sonnet-20240229"   # :1463
continuous_llm_calls(chat_gpt, content=joint_message + "\n\n" + gha_files_to_change_prompt,
    model=MODEL, temperature=0.1, stop_sequences=["</reflection>"], response_cleanup=cleanup_fcrs, MAX_CALLS=10, use_openai=use_openai)
chat_gpt.messages[-1].content += "</reflection>\n"              # close the tag the stop sequence cut off
chat_gpt.messages[0].content = gha_files_to_change_system_prompt_2   # :1475 — SYSTEM PROMPT SWAP mid-conversation
files_to_change_response = continuous_llm_calls(chat_gpt, content=gha_files_to_change_prompt_2,
    model=MODEL, temperature=0.1, stop_sequences=["</plan>"], response_cleanup=cleanup_fcrs, MAX_CALLS=10, use_openai=False) + "\n</plan>"   # :1484 hardcoded False
...
error_message, error_indices = get_error_message(file_change_requests, cloned_repo, updated_files)   # :1509 — updated_files POSITIONAL
for _ in range(3):                                               # ≤3 repair rounds
    if not error_message: break
    chat_gpt.messages = [message for message in chat_gpt.messages if message.key != "system"]
    fix_attempt = continuous_llm_calls(..., stop_sequences=["</error_resolutions"], ...)             # :1523 — missing closing bracket
    drops, matches = parse_patch_fcrs(fix_attempt)
    for index, new_fcr in matches:
        if new_fcr.change_type == "create" and "COPIED_FROM_PREVIOUS_CREATE" in new_fcr.instructions:
            file_change_requests[error_indices[index]].filename = new_fcr.filename                   # filename-only override
            continue
        file_change_requests[error_indices[index]] = new_fcr
    for drop in sorted(drops, reverse=True): file_change_requests.pop(error_indices[drop])
    error_message, error_indices = get_error_message(file_change_requests, cloned_repo, updated_files)
set_fcr_change_type(file_change_requests, cloned_repo)
return file_change_requests, files_to_change_response
except RegexMatchError as e: ...
return [], ""
```

**Flow:** both call sites build the problem statement from GHA_PROMPT (first pass) or GHA_PROMPT_WITH_HISTORY (retry: adds previous failing logs + diffs of what was already changed), run prep_snippets, then pass ONLY `snippets[:10]` with empty read_only list and `updated_files=modify_files_dict` (the first attempt's results) and use_openai=True → inside the variant, snippet contents are SWAPPED to the post-change text before any rendering (the planner must reason about the current state of the files, not the pre-fix state) → interleave + the SHARED get_max_snippets budget kernel (≤15 snippets / 525k-char prefix, see llm-file-selection-budget-plane) then re-split by membership in the original relevant list → templates: read_only under `<relevant_read_only_snippets>` as `<read_only_snippet>`; relevant as `<relevant_file>` with source-type snippets expand(300) → optional `<file_paths_in_context>` message when use_faster_model, whose CLOSING tag is malformed (the opening tag string is reused, :1446) → STAGE 1 runs under the analysis system prompt with stop_sequences=["</reflection>"] and response_cleanup=cleanup_fcrs; the truncated last message is closed with a literal "</reflection>
" append → the SYSTEM message is then swapped in place to the writing prompt and STAGE 2 runs with stop_sequences=["</plan>"] and use_openai=False HARDCODED (both call sites pass True — the flag only survives stage 1; without an Anthropic key chat.py:369–370 still flips to gpt-4o) → parse `<relevant_modules>` (DOTALL) and stamp `" ".join(modules)` as raw_relevant_files on EVERY FCR; FCRs via FileChangeRequest._regex finditer → repair loop ≤3 rounds against get_error_message with updated_files passed POSITIONALLY (so validation checks original_code against POST-change contents — see fcr-prevalidation-plane): each round strips system-keyed messages from history, sends the fix prompt with allowed_indices, parses `<fix index>`/`<drop index>` patches, replaces FCRs at error indices (COPIED_FROM_PREVIOUS_CREATE overrides filename only), pops drops in REVERSE order, re-validates → set_fcr_change_type against disk truth before return; RegexMatchError degenerates to ([], "").
**Invariant:** The two-stage split encodes "analyze before writing": stage 1 is stopped by its own `</reflection>` tag and stage 2 inherits the conversation with a DIFFERENT system prompt — the model's analysis is retained as context while its role changes. A port that merges the stages loses the reflection artifact; one that resets history between them loses the analysis. Content-swap-before-render is the load-bearing difference vs the live planner: autofix plans are plans about ALREADY-MODIFIED files, so every downstream check (pre-validation, apply-loop matching) must also run against updated_files — the positional third argument at :1509 is the coupling point. The repair loop shares the exact index grammar of the live planner (llm-plan-continuation-and-repair): same parse_patch_fcrs, same reverse-order drops, same COPIED_FROM_* filename-only override class. The hardcoded use_openai=False in stage 2 plus the opus pin means the shipped behavior is env-dependent in a way no caller can control (Anthropic key present ⇒ opus wire format; absent ⇒ gpt-4o).
**Probe:** No offline-runnable test covers this variant at pin (import chain needs anthropic/openai/parea/tiktoken; tests/e2e/* need GITHUB_PAT/live API — standing block). Deterministic probes executed at pin: `grep -n 'def get_files_to_change_for_gha' sweepai/core/sweep_bot.py` → :1360 only; `grep -n 'MODEL = "claude-3-opus' sweepai/core/sweep_bot.py` → :495,:810,:1131,:1310,:1463 (five planner pins; :1463 is the GHA variant's and the only one with the use_faster_model sonnet ternary); `grep -n 'stop_sequences=\["</reflection>"\]' sweepai/core/sweep_bot.py` → :1469 only; `grep -n 'stop_sequences=\["</error_resolutions"\]' sweepai/core/sweep_bot.py` → :672,:988,:1523 (all three repair loops share the malformed stop tag; :1523 is the GHA variant's, missing closing bracket confirmed); `grep -n 'use_openai=False' sweepai/core/sweep_bot.py` → :1484 only (the single hardcoded False in the planner file — stage 2 of the GHA ladder); `grep -n 'get_error_message(file_change_requests, cloned_repo, updated_files)' sweepai/core/sweep_bot.py` → :1509,:1545; `grep -n 'file_paths_in_context' sweepai/core/sweep_bot.py` → :1440,:1446 (opening tag reused as closing); `grep -n 'get_files_to_change_for_gha(' sweepai/handlers/on_failing_github_actions.py` → :178,:363; `grep -n 'GHA_PROMPT.format\|GHA_PROMPT_WITH_HISTORY.format' sweepai/handlers/on_failing_github_actions.py` → :159/:166 and :344/:351; `grep -n 'snippets\[:10\]' sweepai/handlers/on_failing_github_actions.py` → 2 rows (both call sites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "get_files_to_change_for_gha gha_files_to_change_system_prompt_2 cleanup_fcrs GHA_PROMPT_WITH_HISTORY on_failing_github_actions", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// sweep_bot.py:1360-1554, prompts.py:368-430, on_failing_github_actions.py:159-183/:344-367 at pin
// substituted — see verification.md pass 6.
```

## Verdict
Adopt the analyze-then-write two-stage ladder with the in-place system-prompt swap (one conversation, two roles, the reflection retained as context), the stop-tag-then-close pattern (append the literal closing tag the stop sequence cut off before continuing), and the content-swap-before-render rule for any planner that reasons over already-modified state. Reuse the shared budget kernel and the index-addressed repair grammar rather than forking them — the GHA variant proves the repair loop is portable across planners when the validation plane takes the same updated_files argument. Adapt: make stage 2's provider flag consistent with stage 1 instead of hardcoded False; fix or deliberately keep the malformed `<file_paths_in_context>` closing tag (models tolerate it, but it is a latent parsing hazard for stricter consumers); decide whether the 10-snippet cap at the call sites should be a parameter. Omit: the print("messages") full-conversation stdout dump, the breakpoint() remnants, and the pylint-disable comment noise. Coverage caveat: no live direct test at pin; firing gates are covered by gha-autofix-attribution-chain, this capsule owns the planning body only.
