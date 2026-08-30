<!-- capsule-v2 -->
# Repair-prompt corpus — how do you turn every validation failure into a self-teaching repair prompt?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; direct source reads (Codebase Memory MCP not connected this session). **Question:** When the model's edit fails validation, how do you make the error message itself teach the correct next call instead of just failing?

## make_change error ladder: every failure mode has a dedicated recipe prompt
**Path/Symbol:** `sweepai/agents/modify_utils.py` — NO_TOOL_CALL_PROMPT (:97–131), EMPTY_ORIGINAL_CODE_PROMPT (:133–272), DID_YOU_MEAN_PROMPT (:274–282), self_review_prompt (:284–308), linter_warning_prompt (:310–319), linter_indentation_warning_prompt (:321–333), fix_parentheses_prompt (:335–344), fix_syntax_prompt (:346–357), ORIGINAL_CODE_NOT_FOUND_PROMPT (:359–382), MULTIPLE_OCCURRENCES_PROMPT (:384–403); dispatch sites in handle_function_call (:872–1220).
**Signature:** each prompt is a module-level string constant; the error ladder composes them into `error_message = f"...context..." + PROMPT` and returns `"ERROR\n\n" + error_message` as the next user message.
**Data Shape:** prompts carry structured placeholders ({file_path}, {original_code}, {diff_parentheses}, {parenthesis}, counted open/close tallies) filled from the failed call's own data — the model never has to re-derive what went wrong.

### Decisive source
```python
best_match, best_score = find_best_match(original_code, file_contents)
if best_score > 80:
    surrounding_lines_before, surrounding_lines_after = get_surrounding_lines(file_contents, best_match)
    ...
    best_match_diff = generate_diff(first_diff_text, second_diff_text, n=20)
    error_message = f"The original_code provided does not appear to be present in file {file_name}. ...\nDid you mean the following?\n```\n{best_match}\n```\nHere is the difference ...\n```\n{best_match_diff}\n```\n" + DID_YOU_MEAN_PROMPT
else:
    # cross-file wrong-target scan: same prompt shape but names the OTHER file
...
if current_chunk_occurences > 1 and not replace_all:
    # enumerate ALL occurrences with ±10-line context, each fenced as "Occurrence N:"
...
error_message = f"Error: Invalid code changes have been applied. ...\n```\n{failing_parse}\n```\n\n" + parentheses_message or fix_syntax_prompt   # :1174 — BUG: + binds tighter than or
```
**Flow:** every failure branch computes the most helpful context it can (fuzzy best match + bounded diff, occurrence enumeration with surrounding lines, counted parenthesis tallies) and embeds it in the error, then appends a RECIPE prompt with numbered thinking steps and the exact corrected call format → EMPTY_ORIGINAL_CODE_PROMPT teaches the append recipe (copy anchor verbatim into original_code, paste + extend in new_code, add `<append>true</append>`) — but "append" is NOT in make_change's tool_call_parameters (chat.py:158) and handle_function_call never reads it: the flag is DEAD at pin; the recipe still works because append == replace-anchor-with-anchor+new → linter_warning vs linter_indentation_warning is chosen by an indentation heuristic (original_code leading spaces > new_code leading spaces ⇒ indentation variant :1206–1210) → self_review_prompt is the SUCCESS-path critique checklist (attached after every applied change :953/:1217) → TWO LATENT BUGS at pin: (a) self_review_prompt / linter_warning_prompt / linter_indentation_warning_prompt bodies contain NO {current_task} placeholder — the `.format(current_task=...)` kwarg is silently dropped (str.format ignores unused kwargs), so the promised task context is never interpolated; (b) :1174 `f"..." + parentheses_message or fix_syntax_prompt` — `+` binds tighter than `or`, the f-string is always truthy, so fix_syntax_prompt is UNREACHABLE.
**Invariant:** Error messages are INSTRUCTIONS, not diagnostics: each one must contain (1) what was wrong, (2) the closest correct alternative computed from repo truth, and (3) a step-by-step recipe for the retry. The teaching content is what makes the bounded apply loop converge — without it, retries repeat the same mistake until the attempt budget force-skips. A port must keep the recipe structure even if it rewrites the prose; and must fix the two latent bugs (add the {current_task} placeholders or drop the kwarg; parenthesize the `or`).
**Probe:** tests/test_modify_utils.py covers handle_submit_task (import-blocked offline — standing block since pass 6). Deterministic probes executed at pin: `grep -n "EMPTY_ORIGINAL_CODE_PROMPT" sweepai/agents/modify_utils.py` → :133(def),:873(use); `grep -n "DID_YOU_MEAN_PROMPT" sweepai/agents/modify_utils.py` → :274,:1050; `grep -n "MULTIPLE_OCCURRENCES_PROMPT" sweepai/agents/modify_utils.py` → :384,:1100,:1119,:1121; `grep -n "ORIGINAL_CODE_NOT_FOUND_PROMPT" sweepai/agents/modify_utils.py` → :359,:1070; `grep -n "self_review_prompt" sweepai/agents/modify_utils.py` → :284,:953,:1217; `grep -n "fix_syntax_prompt\|fix_parentheses_prompt" sweepai/agents/modify_utils.py` → :335,:346,:1165,:1174; `grep -n "linter_indentation_warning_prompt" sweepai/agents/modify_utils.py` → :321,:1209; `grep -n '"make_change":' sweepai/core/chat.py` → :158 (no "append" key); `grep -n "tool_call.get(" sweepai/agents/modify_utils.py` → :872,:1011 (replace_all only, never append); `awk 'NR>=284 && NR<=310' + grep -c current_task` → 0 (placeholder absent).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "EMPTY_ORIGINAL_CODE_PROMPT DID_YOU_MEAN_PROMPT MULTIPLE_OCCURRENCES_PROMPT linter_warning_prompt fix_syntax_prompt", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// modify_utils.py:97-403/:872-1220 + chat.py:157-165 at pin substituted — see verification.md pass 9.
```
## Verdict
Adopt the error-as-instruction discipline: compute the closest correct alternative from repo truth, embed it, attach a numbered recipe. Adopt the success-path critique prompt too (cheap self-review after every applied change). Adapt prompt prose to your model family; keep the context-computation (fuzzy match + bounded diff, occurrence enumeration, counted tallies) — that part is machinery, not prose. Fix the two latent bugs on adoption. Omit: the dead `<append>` flag (teach anchor-replacement directly) and the 140-line calculator-test example inside EMPTY_ORIGINAL_CODE_PROMPT (one short example suffices). Coverage caveat: no offline test at pin; prompt effectiveness is untested by construction.
