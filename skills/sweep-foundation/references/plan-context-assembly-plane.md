<!-- capsule-v2 -->
# Plan-context assembly — how is the apply-loop's user message built so the model sees current file state exactly once per file?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; direct source reads (Codebase Memory MCP not connected this session). **Question:** How do you render plan + current task + file contents into one user message without duplicating files or showing stale contents?

## create_user_message: replace-based template assembly with last-occurrence file attachment and reverse-order dedup
**Path/Symbol:** `sweepai/agents/modify_utils.py:create_user_message` (:642–717, carries "TODO: has non-deterministic behavior"), `get_latest_contents` (:835–841), `english_join` (:448–453), `past_tense_mapping` (:733–736), `cloned_repo.get_file_list` (github_utils.py:646).
**Signature:** `create_user_message(fcrs, request, cloned_repo, relevant_filepaths=None, modify_files_dict=None) -> str`; called fresh at loop start (modify.py:117) and re-called after every landed change (:201–208) with the mutated dict.
**Data Shape:** output = `<user_request>` wrapper + template with four slots ({relevant_files}, {files_to_modify_list}, {completed_prompt}, {files_to_modify}); per-FCR message buckets keyed by filename; file contents attached only under the LAST occurrence of each filename.

### Decisive source
```python
files_to_modify_messages = {fcr.filename: "" for fcr in fcrs}
for i, fcr in enumerate(fcrs):
    if i < current_fcr_index:      # past tense
        files_to_modify_messages[fcr.filename] += f"\n\nYou have already {past_tense_mapping[fcr.change_type]} {fcr.filename}, ..."
    elif i == current_fcr_index:   # current task
        files_to_modify_messages[fcr.filename] += f"\n\nYour current task is to {fcr.change_type} {fcr.filename}. ..."
    else:                          # future tense
        files_to_modify_messages[fcr.filename] += f"\n\nYou will later need to {fcr.change_type} {fcr.filename}. ..."
    last_occurence = i
    for j in range(i + 1, len(fcrs)):
        if fcrs[j].filename == fcr.filename:
            last_occurence = j
    if last_occurence == i:        # attach contents ONLY on the last FCR for this file
        if fcr.change_type == "modify":
            if not modify_files_dict:
                ... cloned_repo.get_file_contents(file_path=fcr.filename) ...
            else:                  # the mutated dict IS repo truth mid-run
                latest_file_contents = get_latest_contents(fcr.filename, cloned_repo, modify_files_dict)
...
for fcr in fcrs[::-1]:             # reverse-order assembly dedups by filename
    if fcr.filename in already_added_files:
        continue
    files_to_modify_string += files_to_modify_messages[fcr.filename]
```
**Flow:** assembly uses `.replace()` NOT str.format — file contents may contain braces that would explode a format call → each filename gets ONE bucket accumulating its past/current/future instruction lines, and contents attach only when the forward scan confirms this FCR is the file's last occurrence (so the model sees final-state instructions next to the code) → modify-type renders `<file_to_modify>` with get_latest_contents: the mutated modify_files_dict contents PREFERRED over disk (the dict is repo truth mid-run), disk fallback, FileNotFoundError ⇒ "" — create-type renders `<file_to_create>` with the instructions as body → final assembly iterates fcrs REVERSED deduping by filename, so file blocks appear in REVERSE plan order (a quirk, not a feature) → relevant_filepaths are validated against cloned_repo.get_file_list() (unformatted paths warned+skipped), FCR filenames excluded, rendered as `<relevant_module filename="...">` inside `<relevant_files>` → the whole message is wrapped in `<user_request>` and, after each landed change, re-rendered with the header "Here is the UPDATED user request ... REVIEW THIS CAREFULLY!".
**Invariant:** Each file's contents appear EXACTLY ONCE per message, always beside its last (final-state) instructions, always reflecting the latest applied contents. The dict-over-disk preference is what makes mid-run re-renders correct without touching the clone. Replace-based templating is mandatory when embedding arbitrary file text. A port must keep single-attachment semantics and dict-truth preference; the reverse-order quirk and the non-determinism TODO (dict iteration order) should be fixed, not copied.
**Probe:** No offline test at pin. Deterministic probes executed: `grep -n "def create_user_message" sweepai/agents/modify_utils.py` → :642 (with TODO comment); `grep -n "last_occurence" sweepai/agents/modify_utils.py` → :671,:675,:676; `grep -n "get_latest_contents" sweepai/agents/modify_utils.py` → :681,:835(def),:1008,:1013,:1053; `grep -n "relevant_module" sweepai/agents/modify_utils.py` → :711; `grep -n "user_request" sweepai/agents/modify_utils.py` → :716; `grep -n "non-deterministic" sweepai/agents/modify_utils.py` → :642; `grep -n "fcrs\[::-1\]" sweepai/agents/modify_utils.py` → :702; `grep -n "get_file_list" sweepai/utils/github_utils.py` → :646(def),:703,:771.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "create_user_message files_to_modify relevant_module get_latest_contents past_tense_mapping", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// modify_utils.py:642-717/:835-841 + github_utils.py:646-660 at pin substituted — see verification.md pass 9.
```
## Verdict
Adopt the assembly discipline: one bucket per file, contents on last occurrence only, dict-truth-over-disk, replace-based templating, validated relevant-modules block. Adopt the re-render-on-change pattern (fresh state message after every landed edit) — it pairs with the system-only context reset in fcr-application-loop. Fix on adoption: forward-order assembly (drop the reverse quirk) and deterministic ordering. Omit: the "REVIEW THIS CAREFULLY" shouting if your model tolerates calmer framing. Coverage caveat: no offline test at pin; the non-determinism TODO in the source itself is unresolved.