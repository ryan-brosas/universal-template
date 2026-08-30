<!-- capsule-v2 -->
# Comment-header rendering plane — how does one mutable progress comment render its states, and how are stale bot PRs cleaned up?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What decides what the top of Sweep's single progress comment shows at each step, and how does a re-run find and delete the previous bot PR?

## get_comment_header index ladder + delete_old_prs literal-body-marker identity
**Path/Symbol:** `sweepai/utils/ticket_rendering_utils.py:get_comment_header` (:247–293), `delete_old_prs` (:231–245), `process_summary` (:295–340), `create_error_logs` (:132–161); deletion guard `sweepai/handlers/create_pr.py:safe_delete_sweep_branch` (:152–176).
**Signature:** `get_comment_header(index: int, progress_headers: list[None | str], payment_message_start: str, errored: bool = False, pr_message: str = "", done: bool = False, config_pr_url: str | None = None) -> str`; `delete_old_prs(repo: Repository, issue_number: int) -> None`.
**Data Shape:** `index` is the step ordinal into `progress_headers` (the step list rendered in the comment body); the header is an HTML/Markdown string with an external progress-bar.dev image. PR identity for deletion is a LITERAL substring of the PR body.

### Decisive source
```python
if index < 0:
    index = 0
if index == 4:
    return pr_message + config_pr_message + f"\n\n{actions_message}"   # TERMINAL state, no pbar
total = len(progress_headers)
index += 1 if done else 0
index *= 100 / total
index = min(100, int(index))
if errored:
    pbar = f"\n\n<img src='https://progress-bar.dev/{index}/?&title=Errored&width=600' ...>"
    return f"{center(sweeping_gif)}<br/>{center(pbar)}\n\n{actions_message}"   # no payment/config msgs
...
# delete_old_prs :231-245:
for pr in tqdm(prs.get_page(0)):                       # PAGE 0 ONLY
    if pr.user.login == CURRENT_USERNAME and f"Fixes #{issue_number}.\n" in pr.body:
        safe_delete_sweep_branch(pr, repo)             # branch-only; pr.edit close commented out
        break                                          # at most ONE old PR per run
```

**Flow:** every `edit_sweep_comment(message, step_index)` re-renders the header from `(step_index, len(progress_headers), done, errored)`: negative index clamps to 0; step 4 is the terminal layout (PR message + optional config-PR link + restart button, no progress bar); otherwise percent = `int((index + done) * 100 / total)` capped at 100, rendered as a progress-bar.dev image plus the payment message and always-present RESTART_SWEEP_BUTTON. On a re-run, `delete_old_prs` scans open PRs on the default branch (created-desc, first page only) and deletes the branch of the first bot-owned PR whose body contains the exact marker `Fixes #N.\n` — a marker written by the PR-description writers (`pull_request_bot.py:166–169` and `ticket_rendering_utils.py:382–385`), so deletion and creation are coupled by that literal string (and `on_comment.py:95` reverse-parses it with a regex). `safe_delete_sweep_branch` then re-checks that ALL commit authors are the bot and the branch starts with "sweep" before deleting the branch (never the PR). `process_summary` pre-cleans the issue body (strips `<details>` Checklist blocks, `--- Checklist:` lists, `### Details\n\n_No response_`, collapses blank lines) and extracts an optional `Branch:` override (quote/backtick-stripped; GitHub tree URLs reduced via `split("?")[0].split("tree/")[-1]`). `create_error_logs` wraps each sandbox output in its own collapsible with the LAST one open by default.
**Invariant:** The header is a PURE function of (step, total, done, errored) — no hidden state, so re-rendering the same comment at any point is idempotent. The terminal state (index==4) must bypass the percentage math entirely or a 4-step pipeline renders 100%+ on completion. Deletion identity is deliberately two-layered: the body marker finds the candidate, the commit-author check vetoes it if a human touched the branch — and only one PR is deleted per run (`break`), so repeated runs converge rather than mass-delete. The `stars_suffix` condition `index != -1` is dead (index ≥ 0 after clamp).
**Probe:** No offline unit test exists (live-GitHub harness only — coverage caveat). Deterministic probes at pin: `grep -c 'progress-bar.dev' sweepai/utils/ticket_rendering_utils.py` → 2; `grep -n 'Fixes #{issue_number}' sweepai/utils/ticket_rendering_utils.py` → :242; `grep -c 'RESTART_SWEEP_BUTTON' sweepai/utils/ticket_rendering_utils.py` → 2 (import + header actions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "comment header progress bar delete old prs fixes issue", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source read of
// ticket_rendering_utils.py:132-161/:231-340 + create_pr.py:152-176 at pin substituted — see verification.md pass 3.
```

## Verdict
Adopt the pure-function header ladder (clamp → terminal-state bypass → percent math → error variant), the two-layered old-PR deletion (template-literal body marker + all-commits-by-bot veto, branch-only, one per run), and the issue-body regex pre-clean with branch-override extraction. Adapt the marker string to your PR template and keep both sides in sync; replace the external progress-bar.dev image with your own renderer. Omit the dead `stars_suffix` condition and the legacy Assistant API plumbing.
