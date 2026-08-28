<!-- capsule-v2 -->
# Task-progress state machine — how does the apply loop know a task is actually done, and how do counters gate lazy vs LLM application?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; direct source reads (Codebase Memory MCP not connected this session). **Question:** How do you decide "this FCR is finished" from tool calls alone, and how do the counters decide when the LLM can be skipped entirely?

## llm_state counters: changes_per_fcr vs completed_changes_per_fcr, attempt_lazy_change, attempt_count, visited_set, done_counter
**Path/Symbol:** `sweepai/agents/modify.py:llm_state` init (:95–111), `sweepai/agents/modify_utils.py` — get_replaces_per_fcr (:774–786), handle_submit_task (:897–919), finish_applying_changes (:960–978), get_current_task_index (:758–764), tasks_completed (:809–811), changes_made (:720–731), generate_diffs (:813–821), error-path force-skip (:1181–1196), success ladder (:1197–1220).
**Signature:** `get_replaces_per_fcr(fcr) -> int` (regex-counted original/new pairs; -1 on mismatch; create ⇒ 1); `get_current_task_index(fcrs) -> int` (first not-completed; annotation lies: declared `-> str`); `generate_diffs(modify_files_dict) -> bool` (annotation lies: declared `-> dict[str, str]`).
**Data Shape:** llm_state = {changes_per_fcr: [int], completed_changes_per_fcr: [int], attempt_lazy_change: bool, attempt_count: int, visited_set: set[str], done_counter: int, fcrs, current_task, plan, request, status_messages, initial_check_results, user_message_index×2}.

### Decisive source
```python
def handle_submit_task(modify_files_dict, llm_state):
    current_fcr_index = get_current_task_index(llm_state["fcrs"])
    llm_state["completed_changes_per_fcr"][current_fcr_index] += 1
    changes_made = generate_diffs(modify_files_dict)
    if changes_made:
        llm_response = "DONE"
    else:
        llm_state["done_counter"] += 1
        if llm_state["done_counter"] > 3:
            llm_response = "DONE"                      # forced DONE after 3 empty submits
    for fcr in llm_state["fcrs"]:
        if not fcr.is_completed:
            fcr.is_completed = True                    # FIRST incomplete FCR marked done
            break
    llm_state["attempt_count"] = 0
    llm_state["attempt_lazy_change"] = True            # re-arm lazy application
    llm_state["visited_set"] = set()                   # dedup state resets per task
```
**Flow:** a task completes through exactly two doors: submit_task (counts only if generate_diffs says contents actually changed — no-change submits burn done_counter, >3 forces DONE so a stuck model cannot loop forever) or the auto-continue tail finish_applying_changes when a make_change exhausts the FCR's pair counter → both doors mark the FIRST incomplete FCR, reset attempt_count=0, re-arm attempt_lazy_change=True, clear visited_set, and re-render current_task into the SUCCESS message so the next round's mock/lazy decision uses fresh state → the next-round ladder (modify.py:237–286) prefers NO LLM: pair counter met ⇒ mock submit_task; else attempt_lazy_change ⇒ compile_fcr fake-injection; only then a real call → make_change success ladder (:1197–1220): linter warning ⇒ SUCCESS+linter prompt+attempt_lazy_change=False (warnings disable lazy application — the model must look before the next fake call); incomplete ⇒ SUCCESS+self_review+counter++; else auto-continue → error path (:1181–1196): attempt_count++; >5 ⇒ force-complete the first incomplete FCR ("SKIPPED") and reset — a permanently failing task cannot consume the whole 15×N budget → handle_create_file has a dead `if new_file_name not in modify_files_dict` branch (always false right after assignment) and renders generate_diff(x, x) — always empty.
**Invariant:** Every counter has an escape hatch that terminates: done_counter>3, attempt_count>5, visited_set dedup, and the 15-rounds-per-FCR budget. "Done" is defined by CONTENT DIFF, never by the model's claim — submit_task without changes is not progress. Lazy application is armed only after a clean completion; any warning or error disarms it, forcing the model to observe state before the next zero-cost fake call. A port must keep "done = diff exists" and every termination hatch; annotation bugs (-> str / -> dict lies) should be fixed, not copied.
**Probe:** tests/test_modify_utils.py::test_handle_submit_task covers this exact function (MagicMock fcrs) but is import-blocked offline (rapidfuzz chain) — standing block since pass 6. Deterministic probes executed at pin: `grep -n "attempt_lazy_change" sweepai/agents/modify_utils.py sweepai/agents/modify.py` → :918,:976,:1183,:1195,:1214,:1219 + modify.py:107,:245; `grep -n "done_counter" sweepai/agents/modify_utils.py` → :901,:903,:905 (init :100 in modify.py); `grep -n "def get_current_task_index" -A1 sweepai/agents/modify_utils.py` → :758 `-> str` annotation, returns int; `grep -n "def generate_diffs" -A1 sweepai/agents/modify_utils.py` → :813 `-> dict[str, str]` annotation, returns bool; `grep -n "generate_diff(new_file_contents, new_file_contents" sweepai/agents/modify_utils.py` → :953 (empty diff); `grep -n "for _ in range(1)" sweepai/agents/modify_utils.py` → :1000 (jank single-iteration loop); `grep -n "attempt_count" sweepai/agents/modify_utils.py` → :916,:974,:1183,:1189,:1193,:1206,:1213,:1216.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "handle_submit_task finish_applying_changes get_replaces_per_fcr attempt_lazy_change done_counter visited_set", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// modify.py:95-111/:237-286, modify_utils.py:720-821/:897-978/:1181-1220 at pin
// substituted — see verification.md pass 9.
```
## Verdict
Adopt the counter machine: done-by-diff, per-task attempt cap with force-skip, lazy-application arming/disarming, and per-task reset of dedup state. Adopt "counters decide when the LLM is skipped" — the mock/lazy/real ladder is the cost model. Adapt budget constants to your latency tolerance. Fix on adoption: the two annotation lies, the dead create_file branch, and the always-empty create_file diff (render generate_diff("", contents)). Omit: the single-iteration `for _ in range(1)` error-handling wrapper (use a labeled break or extract a function). Coverage caveat: the one direct test (test_handle_submit_task) is import-blocked offline; behavior pinned by probes only.