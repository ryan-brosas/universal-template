<!-- capsule-v2 -->
# improve-loop-refinement-cap — How many chances does the model get to fix malformed diffs?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What is the edit-refinement retry loop, its bound, and its feedback-message contract?

## Improve refinement loop seam
**Path/Symbol:** `gpt_engineer/core/default/steps.py:_improve_loop` (:315-338) fed by `improve_fn` (:271-312); bound constant `gpt_engineer/core/default/constants.py:MAX_EDIT_REFINEMENT_STEPS = 2`.
**Signature:** `_improve_loop(ai, files_dict: FilesDict, memory: BaseMemory, messages: List, diff_timeout=3) -> FilesDict`.
**Data Shape:** messages accumulate: [system, Human(files as to_chat()), Human(prompt), AIMessage(diffs), Human(feedback), AIMessage(fixed diffs)...]; returns updated FilesDict.

### Decisive source
```python
messages = ai.next(messages, step_name=curr_fn())
files_dict, errors = salvage_correct_hunks(messages, files_dict, memory, diff_timeout=diff_timeout)
retries = 0
while errors and retries < MAX_EDIT_REFINEMENT_STEPS:
    messages.append(HumanMessage(
        content="Some previously produced diffs were not on the requested format, or the code part was not found in the code. Details:\n"
        + "\n".join(errors)
        + "\n Only rewrite the problematic diffs, making sure that the failing ones are now on the correct format and can be found in the code. Make sure to not repeat past mistakes. \n"))
    messages = ai.next(messages, step_name=curr_fn())
    files_dict, errors = salvage_correct_hunks(messages, files_dict, memory, diff_timeout)
    retries += 1
return files_dict
```

**Flow:** first inference over [sys, files, prompt] → salvage attempt → while unresolvable errors AND retries<2: append error-details feedback asking to rewrite ONLY problematic diffs → re-infer → re-salvage.
**Invariant:** (1) Bound counts RETRIES (2), so the model gets at most 3 total attempts (initial + 2 refinements) before whatever partial application happened stands. (2) Each salvage round starts FROM the previously patched files_dict — successful hunks persist across rounds; failed hunks are retried against already-modified code (line numbers shift!). (3) The feedback message enumerates validator problems verbatim — error strings ARE the repair interface; keep their phrasing stable when porting. (4) `diff_timeout` threads through everywhere: it bounds the catastrophic-backtracking-prone diff regex (third-party `regex` module), CLI exposes it as `--diff_timeout`.
**Probe:** `cat gpt_engineer/core/default/constants.py | grep MAX_EDIT_REFINEMENT_STEPS` → `MAX_EDIT_REFINEMENT_STEPS = 2`.
**Probe:** `grep -c 'salvage_correct_hunks' gpt_engineer/core/default/steps.py` → 3 (import + 2 loop calls).
**Probe:** `tests/applications/cli/test_main.py::test_improve_existing_project_diff_timeout` proves diff_timeout plumbs from CLI to the loop.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "_improve_loop MAX_EDIT_REFINEMENT_STEPS errors retries", limit: 10 });
```

## Verdict
Adopt the bounded salvage-feedback loop shape (cap, verbatim error echo, cumulative patch base) for any LLM-edit pipeline; adapt cap value to model reliability; omit the specific English phrasing only if you keep equivalent specificity.
