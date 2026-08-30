<!-- capsule-v2 -->
# Stateful suggestion streaming — how do you stream per-file apply progress to both a silent caller and a live UI without duplicating the loop?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; direct source reads (Codebase Memory MCP not connected this session). **Question:** After the planner emits FCRs, how does the apply loop expose live per-file progress to a browser while the ticket path consumes only the final dict?

## generate_code_suggestions: one snapshot renderer, two consumers via @streamable duality
**Path/Symbol:** `sweepai/agents/modify.py:generate_code_suggestions` (:17–59), `modify` yield sites (:157, :318), `sweepai/dataclasses/code_suggestions.py` (whole, 12L), `sweepai/utils/streamable_functions.py` (@streamable), consumers `sweepai/handlers/create_pr.py:71` (plain call) and `sweepai/chat/api.py:870` (modify.stream()).
**Signature:** `generate_code_suggestions(modify_files_dict, fcrs, error_messages_dict, cloned_repo) -> list[StatefulCodeSuggestion]`; `StatefulCodeSuggestion(file_path, original_code, new_code, file_contents, state: Literal["pending","processing","done","error"], error: str|None)`.
**Data Shape:** done files carry the full original_contents/contents pair; not-yet-done FCRs carry only the FIRST parsed original/new code pair (`parsed_fcr["original_code"][0]`) plus the file's on-disk contents and the per-index error message from `get_error_message_dict`; missing files degrade to `file_contents=""`.

### Decisive source
```python
current_fcr_index = next((i for i, fcr in enumerate(fcrs) if not fcr.is_completed), -1)
if current_fcr_index >= 0:
    for i, fcr in enumerate(fcrs):
        if i < current_fcr_index:
            continue
        else:
            parsed_fcr = parse_fcr(fcr)
            try:
                file_contents = cloned_repo.get_file_contents(fcr.filename)
            except FileNotFoundError:
                file_contents = ""
            code_suggestions.append(StatefulCodeSuggestion(
                file_path=fcr.filename,
                original_code=parsed_fcr["original_code"][0] if parsed_fcr["original_code"] else "",
                new_code=parsed_fcr["new_code"][0] if parsed_fcr["new_code"] else "",
                file_contents=file_contents,
                state=("processing" if i == current_fcr_index else "pending"),
                error=error_messages_dict.get(i, None)
            ))
```
**Flow:** modify() yields one snapshot at the TOP of every loop round (:157) and one final post-formatter snapshot before returning (:318) — the UI sees done/processing/pending states advance in real time while the loop runs → the same generator serves two consumers through the @streamable duality (streamable-function-duality capsule): `create_pr.py:71` calls `modify(...)` plainly, drains the yields, and uses only the returned modify_files_dict; `chat/api.py:870` iterates `modify.stream(...)` and JSON-dumps each snapshot list to the browser as a StreamingResponse, with exceptions yielded as `{"error": str(e)}` and then re-raised → the chat plane pre-seeds the same shape: pending suggestions are stamped into message annotations with `state: "pending"` (:731) and errors from get_error_message_dict are written back per index (:752–757).
**Invariant:** The snapshot is a PROJECTION, never the working state: it is rebuilt from scratch each round from modify_files_dict + fcrs, so a crash mid-round loses nothing and the UI can never observe a half-mutated dict. Done files are distinguished from pending ones by carrying full contents; pending files intentionally show only the planned first pair. A port must keep the renderer pure (no mutation of loop state) — that is what makes one loop safely serve both a fire-and-forget caller and a live UI.
**Probe:** No offline test covers this plane (import chain blocked; rerun harness needs live GitHub). Deterministic probes executed at pin: `grep -n "StatefulCodeSuggestion" sweepai/agents/modify.py` → :22,:33,:52; `grep -rn "StatefulCodeSuggestion" sweepai --include="*.py"` → modify.py (3) + dataclasses/code_suggestions.py only; `grep -rn "modify.stream" sweepai --include="*.py"` → chat/api.py:870 only; `grep -n "modify(" sweepai/handlers/create_pr.py` → :71; `grep -n "state.*pending" sweepai/chat/api.py` → :731 `"state": "pending"`; `grep -c "def " sweepai/dataclasses/code_suggestions.py` → 0 (two plain @dataclass declarations: CodeSuggestion + StatefulCodeSuggestion).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "generate_code_suggestions StatefulCodeSuggestion modify.stream StreamingResponse", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// modify.py whole, dataclasses/code_suggestions.py whole, chat/api.py:855-880, create_pr.py:55-90
// at pin substituted — see verification.md pass 9.
```
## Verdict
Adopt the single pure snapshot renderer + @streamable duality: one loop, one projection function, two consumers with zero duplicated progress logic. Adapt the state enum to your host's UI vocabulary and consider adding a per-file "error" state on the streaming path (the chat plane already threads per-index errors into annotations). Omit: the first-pair-only preview for pending files if your UI can afford full diffs, and the CWD-relative StreamingResponse wiring. Coverage caveat: no offline test at pin; the chat-plane consumer is exercised only by live browser sessions.
