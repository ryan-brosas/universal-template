<!-- capsule-v2 -->
# FCR application loop — how do you apply LLM-parsed file change requests to real files with a bounded tool-call loop, lazy application, and context reset?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** After the planner emits FileChangeRequests, how does Sweep actually turn them into file contents — iteration budget, when the LLM is skipped entirely, how repeated failures are capped, and how long runs avoid context rot?

## modify(): 15-iterations-per-FCR tool-call loop with fake-injected lazy calls and system-only context reset
**Path/Symbol:** `sweepai/agents/modify.py:modify` (:63–327, @streamable), `generate_code_suggestions` (:17–59); state machine in `sweepai/agents/modify_utils.py:handle_function_call` (:980–1230), `handle_submit_task` (:897–919), `finish_applying_changes` (:960–978), `compile_fcr` (:787–807), `changes_made` (:720–731), `tasks_completed` (:809–811). **Live callers:** `sweepai/handlers/create_pr.py:71` (ticket path) and `sweepai/chat/api.py:17` (chat plane).
**Signature:** `modify(fcrs, request, cloned_repo, relevant_filepaths, chat_logger=None, use_openai=False, previous_modify_files_dict={}, renames_dict={}, raise_on_max_iterations=False) -> dict[str, dict[str, str]]`; yields `list[StatefulCodeSuggestion]` each iteration; returns `{file: {"contents", "original_contents"}}`.
**Data Shape:** input = parsed FCR list + cloned repo on disk; output = per-file original/new contents dict; the LLM conversation is the mutable state (`chat_gpt.messages` + `llm_state`).

### Decisive source
```python
use_openai = False                      # :75 — the parameter is FORCED off, dead argument
for file_path, new_file_path in renames_dict.items():   # :78 — renames applied PHYSICALLY pre-loop
    file_contents = cloned_repo.get_file_contents(file_path)
    with open(os.path.join(cloned_repo.repo_dir, new_file_path), "w") as f:
        f.write(file_contents)
    os.remove(os.path.join(cloned_repo.repo_dir, file_path))
...
for i in range(len(fcrs) * 15):         # :156 — hard budget: 15 tool-call rounds per FCR
    yield generate_code_suggestions(modify_files_dict, fcrs, error_messages_dict, cloned_repo)
    function_call = validate_and_parse_function_call(function_calls_string, chat_gpt)
    ...
    if changes_made(modify_files_dict, previous_modify_files_dict) and current_num_of_tasks_done > num_of_tasks_done:
        chat_gpt.messages = chat_gpt.messages[:1]      # :210 — collapse to SYSTEM message only
        chat_gpt.messages.append(Message(role="user", content=user_message))  # fresh "UPDATED … REVIEW THIS CAREFULLY!"
...
    if change_in_fcr_index >= max_changes:
        function_calls_string = SUBMIT_TASK_MOCK_FUNCTION_CALL.format(justification=f"Task {current_fcr_index} is now complete.")
    else:
        if llm_state["attempt_lazy_change"]:
            if compiled_fcr := compile_fcr(fcrs[current_fcr_index], change_in_fcr_index):
                function_calls_string = compiled_fcr   # FAKE assistant message — no LLM call
                chat_gpt.messages.append(Message(role="assistant", content=function_calls_string))
        if not function_calls_string:
            if linter_warning_prompt in function_output:
                llm_state["attempt_count"] = 3          # skip to SLOW_MODEL
            model = MODEL if llm_state["attempt_count"] < 3 else SLOW_MODEL   # :259 — BOTH are claude-3-5-sonnet-20240620 at pin
            function_calls_string = continuous_llm_calls(...)
            if function_calls_string in llm_state["visited_set"]:   # :268 — identical-output dedup
                ... escalate attempt_count=3, retry once, else SUBMIT_TASK_MOCK "Skipping task N due to too many retries."
...
for file_path, file_data in modify_files_dict.items():   # post-loop formatter guard
    formatted_contents = format_file(file_path, file_data["contents"], cloned_repo.repo_dir)
    # only accept the changes if the formatted contents would not revert all changes
    if file_data["original_contents"] != formatted_contents:
        file_data["contents"] = formatted_contents
```

**Flow:** renames are physically applied to the clone BEFORE any LLM work (copy + os.remove; a TODO admits deletions are unhandled) → first call is lazy: `compile_fcr(fcrs[0], 0)` turns the FCR's own `<original_code>`/`<new_code>` pair into a synthetic assistant tool-call message so the apply machinery runs with zero LLM cost; only an uncompilable FCR triggers a real `continuous_llm_calls` → the main loop runs at most `len(fcrs) * 15` rounds, yielding StatefulCodeSuggestion snapshots (done / processing / pending + per-index errors) every round → each round parses the pending function call string (tolerant: appends a closing `</function_call>` before parsing, modify_utils.py:625–640) and dispatches make_change / create_file / submit_task through handle_function_call → on DONE the full diff is logged to chat_logger and the loop breaks → after every successful change that also advanced the task counter, history collapses to `messages[:1]` (system) plus ONE fresh user message re-rendered from current state — long multi-file runs never accumulate stale intermediate state → the next-round decision ladder prefers NO LLM: completed-changes counter met ⇒ mock submit_task; else lazy compile_fcr fake-injection; only then a real call, escalating MODEL→SLOW_MODEL at attempt_count ≥ 3 (a no-op at pin — both constants are the same model string) and skipping straight to 3 on linter warnings → visited_set dedup catches the model repeating an identical tool call: one escalated retry, then the task is force-skipped via a mock submit_task → any exception during the LLM call dumps msg.txt to CWD and breaks; hitting the for-else budget raises only when raise_on_max_iterations → post-loop, format_file (prettier/formatter) runs per file but its output is accepted ONLY IF it does not revert all changes (formatter-out-of-sync protection).
**Invariant:** The loop is BOUNDED by construction: 15 rounds per FCR, per-task attempt cap (>5 errors ⇒ force-complete the FCR and move on, modify_utils.py:1185–1196), done_counter > 3 ⇒ forced DONE on empty submits, and identical-output dedup ⇒ skip. A port must keep every escape hatch terminating — the failure modes here are infinite LLM loops and quota burn, not wrong edits. Lazy application is load-bearing: well-formed FCRs should never pay for an LLM round-trip, which means the planner's output grammar (original/new code pairs) doubles as an executable program. The context-reset rule (system-only + one fresh state message, fired only when BOTH a change landed AND the task counter advanced) is what makes 15×N budgets affordable; resetting on every round would lose the error-feedback conversation, never resetting would rot it. The formatter guard encodes "the formatter may be out of sync with the repo" — accept formatting only when it preserves the change. `use_openai` being force-false means the Anthropic wire format is the only real path in this agent regardless of caller intent.
**Probe:** No offline-runnable test covers modify() at pin (import chain needs rapidfuzz/stringzilla/anthropic/openai/parea; tests/test_modify_utils.py exists but is import-blocked — see search-replace-match-ladder capsule). Deterministic probes executed at pin: `grep -n 'use_openai = False' sweepai/agents/modify.py` → :75 only; `grep -n 'for i in range(len(fcrs) \* 15)' sweepai/agents/modify.py` → :156 only; `grep -n 'MODEL = "\|SLOW_MODEL = "' sweepai/agents/modify_utils.py` → :622/:623 both "claude-3-5-sonnet-20240620"; `grep -n 'SUBMIT_TASK_MOCK_FUNCTION_CALL' sweepai/agents/modify.py` → :6 (import),:242,:281,:286; `grep -n 'messages = chat_gpt.messages\[:1\]' sweepai/agents/modify.py` → :210 only; `grep -n 'msg.txt' sweepai/agents/modify.py` → :290 only; `grep -rn 'from sweepai.agents.modify import' sweepai/` → create_pr.py:12 + chat/api.py:17 (+ tests/rerun_chat_modify_direct.py:4 harness); `grep -n 'raise_on_max_iterations' sweepai/agents/modify.py` → :72,:303.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "modify compile_fcr SUBMIT_TASK_MOCK_FUNCTION_CALL visited_set generate_code_suggestions handle_function_call", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// modify.py (327L whole) and modify_utils.py :625-1232 at pin substituted — see verification.md pass 6.
```

## Verdict
Adopt the bounded-budget tool-call loop shape (hard N-per-task iteration cap, per-task error-attempt cap with force-skip, identical-output dedup with one escalated retry, mock tool-calls for bookkeeping transitions so the LLM is never asked to do arithmetic), the lazy fake-injection of already-parsed edits (planner output as executable program), and the system-only context reset gated on (change landed AND task advanced). Adapt: pick your own budget constants (15/fcr, >5 attempts, done_counter>3 are tuned to opus-era latency, not laws); make the formatter guard configurable rather than a silent revert-protection; thread use_openai deliberately instead of force-false. Omit: physical rename application inside the agent (do it in the repo layer before planning), the msg.txt CWD debug dump, the `print(function_output)` per-round stdout noise, and the dead use_openai parameter. Coverage caveat: no live direct test at pin; this is the single choke point between plan and commit for the ticket path, so a change here alters every PR Sweep ships.
