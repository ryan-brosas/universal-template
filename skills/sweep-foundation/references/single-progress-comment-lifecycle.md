<!-- capsule-v2 -->
# Single progress-comment lifecycle — how does one mutable comment carry multi-step progress across token expiry?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How does a long-running agent report step-by-step progress on an issue without spamming comments, and how does it survive credential expiry mid-run?

## Reuse-first comment + edit monkey-patch + BadCredentials recovery
**Path/Symbol:** `sweepai/handlers/on_ticket.py:242-344` (`on_ticket` comment reuse; nested `edit_sweep_comment`) (line range); entry parsing `sweepai/utils/str_utils.py:88-99` (`strip_sweep`, graph-confirmed 7-tuple return).
**Signature:** `def edit_sweep_comment(message: str, index: int, pr_message="", done=False, step_complete=True, add_bonus_message=True)` (closure over `past_messages`, `current_index`, `issue_comment`, `user_token`, `g`, `repo`).
**Data Shape:** `progress_headers = [None, "Step 1: 🔎 Searching", "Step 2: ⌨️ Coding", "Step 3: 🔄️ Validating"]`; `past_messages: dict[int, str]`; `index == -1` means terminal error render.

### Decisive source
```python
if issue_comment is None:
    issue_comment = current_issue.create_comment(first_comment)
else:
    fire_and_forget_wrapper(issue_comment.edit)(first_comment)
old_edit = issue_comment.edit
issue_comment.edit = lambda msg: old_edit(msg + BOT_SUFFIX)
```
```python
try:
    issue_comment.edit(msg)
except BadCredentialsException:
    user_token, g = get_github_client(installation_id)
    repo = g.get_repo(repo_full_name)
    issue_comment = None
    for comment in comments:
        if comment.user.login == CURRENT_USERNAME:
            issue_comment = comment
    current_issue = repo.get_issue(number=issue_number)
    if issue_comment is None:
        issue_comment = current_issue.create_comment(msg)
    else:
        issue_comment = [c for c in current_issue.get_comments()
                         if c.user.login == CURRENT_USERNAME][0]
        issue_comment.edit(msg)
```

**Flow:** entry parses mode flags from the title via `strip_sweep` regex (Slow/Map/Subissues/Sandbox/Fast/Lint) → Sweep finds its FIRST existing bot comment on the issue and reuses it, else creates one → the instance's `.edit` is wrapped to always append `BOT_SUFFIX` → every step calls `edit_sweep_comment(message, i)`, which aggregates `past_messages[0..current_index+1]` under step headers ("Working on it..." for pending steps, suppressed when `step_complete=False`) and re-renders the whole comment → error renders use `index=-1` with a distinct "❌ Unable to Complete PR" header and drop the Discord suffix.
**Invariant:** Exactly one Sweep-owned progress comment per issue; every edit is idempotent full-body replacement (never append-only), so partial failures leave a coherent last-rendered state. Credential expiry is recovered by re-fetching client AND re-resolving the comment object — never by letting the run die.
**Probe:** No unit test covers this closure (coverage caveat). Deterministic probe: `strip_sweep("Sweep(Fast): do X")` returns 7-tuple with fast_mode True — verified by reading the six `re.search` patterns in `str_utils.py:88-99`; executed graph retrieve below confirms the symbol at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "issue comment progress headers create_comment bot suffix edit", limit: 8 });
// executed at pin: TicketProgress.load/save nodes api.py progress route + progress.py returned;
// strip_sweep confirmed separately via name/query search (str_utils.py 88-99)
```

## Verdict
Adopt reuse-first single-comment rendering with full-body idempotent edits, step-header aggregation from a message dict, and the refresh-client-and-recover-object ladder; adapt header text/reaction emoji; omit the `.edit` monkey-patch (a readability hazard — wrap in an explicit helper instead) and Sweep's marketing suffixes.
