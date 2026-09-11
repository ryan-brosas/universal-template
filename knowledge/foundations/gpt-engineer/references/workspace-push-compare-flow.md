<!-- capsule-v2 -->
# workspace-push-compare-flow — What is the exact end-of-run sequence that lands generated code on disk?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** In what order do compare/consent/stage/push happen, and what differs between improve and generate tails?

## Terminal flow seam
**Path/Symbol:** `gpt_engineer/applications/cli/main.py` improve tail (:515-540) vs generate tail (:542-550); `compare` (:203-229); `FileStore.push` (`core/default/file_store.py:39-45`).
**Signature:** `main(...)` typer command; `compare(f1: FilesDict, f2: FilesDict)`.
**Data Shape:** Unified diffs colored ANSI (green +, orange-red −) computed with difflib.unified_diff per file over sorted(set(f1)|set(f2)).

### Decisive source
```python
# IMPROVE tail
files_dict_before, is_linting = FileSelector(project_path).ask_for_files(...)
if is_linting: files_dict_before = files.linting(files_dict_before)
files_dict = handle_improve_mode(prompt, agent, memory, files_dict_before, diff_timeout=diff_timeout)
if not files_dict or files_dict_before == files_dict: print("No changes applied...")
else:
    compare(files_dict_before, files_dict)
    if not prompt_yesno(): files_dict = files_dict_before        # reject ⇒ restore original
# GENERATE tail
files_dict = agent.init(prompt)
collect_and_send_human_review(prompt, model, temperature, config, memory)
# SHARED
stage_uncommitted_to_git(path, files_dict, improve_mode)
files.push(files_dict)
```

**Flow:** improve = select→lint→run→(guard)→show-colored-diff→y/n consent (n restores before-state)→git-stage→push; generate = init (gen+entrypoint+process)→optional telemetry review→git-stage(auto-init repo)→push.
**Invariant:** (1) Consent compares OBJECT equality of FilesDict dicts — identical content ⇒ treated as no-op regardless of identity. (2) Rejection path REASSIGNS files_dict to before-state so push() writes ORIGINAL content back (idempotent no-op on disk) rather than skipping push — subtle: push always runs. (3) Linting mutates BEFORE-state (black-formats selected files) meaning accepted diffs include lint churn by design. (4) FileStore.push writes UTF-8 without encoding arg (platform default) and creates parent dirs; pull() tolerates binaries as "binary file" placeholder. (5) Telemetry (collect_and_send_human_review) fires ONLY on generate tail, post-init, consent-gated internally.
**Probe:** `grep -n 'files_dict = files_dict_before' gpt_engineer/applications/cli/main.py` → :540 rejection restore.
**Probe:** `grep -n 'stage_uncommitted_to_git(path, files_dict, improve_mode)' gpt_engineer/applications/cli/main.py` → :548 single shared call site.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "compare prompt_yesno files.push stage_uncommitted_to_git", limit: 10 });
```

## Verdict
Adopt diff-review-consent-restore-before-push as the safe write tail; adapt coloring/UX; preserve restore-not-skip semantics so disk state stays predictable. Note lint-before-diff ordering when porting formatters.
