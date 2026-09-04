<!-- capsule-v2 -->
# Jira multi-forge dispatch — how do you accept a second issue tracker's webhook and reuse one ticket pipeline without duplicating dispatch machinery?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What does a second-forge entry point owe the shared pipeline — auth posture, thread lifecycle, object mirroring, synchronous vs async handoff, result discovery, and the comment-back contract?

## POST /jira → mirror GitHub issue → synchronous on_ticket → marker-based PR discovery → Jira comment-back
**Path/Symbol:** `sweepai/api.py:jira_webhook` (:296–303); `sweepai/handlers/on_jira_ticket.py:handle_jira_ticket` (:27–86), `extract_repo_name_from_description` (:7–15), `comment_on_jira_webhook` (:18–24); config `sweepai/config/server.py:JIRA_API_TOKEN/JIRA_URL/JIRA_USER_NAME`; PR marker reader joins fixes-marker-contract-and-pr-summary-ladder (reader #3).
**Signature:** `jira_webhook(request_dict: dict = Body(...)) -> None` (FastAPI route, NO signature dependency); `handle_jira_ticket(event: dict) -> None` (worker-thread body).
**Data Shape:** input = Jira webhook payload with event["issue"]["fields"]["summary"/"description"] and event["issue"]["key"]; output = a mirrored GitHub issue + whatever on_ticket produces + ONE Jira comment; failure shape = silent (no try/except anywhere in the module).

### Decisive source
```python
@app.post("/jira")                                   # contrast: @app.post("/", dependencies=[Depends(validate_signature)]) at :284
def jira_webhook(request_dict: dict = Body(...)) -> None:
    def call_jira_ticket(*args, **kwargs):
        thread = threading.Thread(target=handle_jira_ticket, args=args, kwargs=kwargs)
        thread.start()
    call_jira_ticket(event=request_dict)

# repo binding is a convention IN THE TICKET BODY, not a webhook field
pattern = r'repo:\s*(\S+/\S+)'                    # "repo: org/name"
repo_full_name = extract_repo_name_from_description(description)
if not repo_full_name:
    return                                           # silent — no Jira comment, no log line

github_issue = repo.create_issue(title=title, body=description)   # MIRROR: Jira ticket becomes a GitHub issue

# wait for this
on_ticket(username=github_issue.user.login, title=title, summary=description,
          issue_number=github_issue.number, ..., comment_id=None, edited=False, tracking_id=None)

# PR discovery AFTER the pipeline finished: page 0 only, literal marker, no bot-login gate
for pr in prs.get_page(0):
    if f"Fixes #{github_issue.number}.\n" in pr.body:
        resolution_pr = pr
        break

jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_USER_NAME, JIRA_API_TOKEN))
jira.add_comment(issue_key, comment_text)
```

**Flow:** unauthenticated POST /jira (no HMAC dependency — trust boundary is network-level only) → spawn a DETACHED threading.Thread(target=handle_jira_ticket) and return None immediately (the Jira side always sees success regardless of outcome) → worker reads summary/description from event["issue"]["fields"] → repo binding via regex r'repo:\s*(\S+/\S+)' on the description; missing ⇒ SILENT return (no comment back, no log) → get_installation_id(org) + get_github_client → repo.create_issue(title, body=description) mirrors the Jira ticket as a GitHub issue → on_ticket is called SYNCHRONOUSLY inside the worker thread (source comment "# wait for this") with comment_id=None/edited=False/tracking_id=None — the thread blocks until the whole ticket (plan, modify, PR) completes → re-fetch client/repo/issue with fresh credentials → scan open PRs sorted created-desc, PAGE 0 ONLY (≤100), first body containing the literal f"Fixes #{n}.\n" marker (marker-contract reader #3; unlike delete_old_prs there is NO bot-login gate) → comment back to Jira via basic_auth=(JIRA_USER_NAME, JIRA_API_TOKEN): always the GitHub issue URL, plus the PR URL only when found. Zero try/except in the module: any exception dies in the detached thread (threading excepthook → stderr) and the Jira side never learns.
**Invariant:** The dispatch layer's only job is MIRRORING + HANDOFF: the Jira object never enters the pipeline — a GitHub issue does — so every downstream consumer (progress comments, PR markers, cron maintenance) stays forge-agnostic. The synchronous on_ticket call is load-bearing: the PR lookup that follows depends on the pipeline having FINISHED, so an async handoff without a completion signal breaks the comment-back contract (it would report "issue created" forever). The missing-repo case must fail CLOSED-and-SILENT from the pipeline's perspective (return before any GitHub write) but that silence is itself a porting hazard — a port should at least log, since the reporter gets no feedback either way. There is NO dedup or latest-wins for Jira tickets: two webhooks for the same ticket spawn two parallel on_ticket runs (contrast latest-wins-ticket-thread-replacement and per-pr-comment-coalescing-queue, which exist only on the GitHub path). The PR scan's page-0 cap and absent bot-login gate mean a user PR whose body happens to contain "Fixes #N.\n" can be misattributed as the resolution PR.
**Probe:** No offline-runnable test exists for on_jira_ticket or the /jira route at pin (tests/ holds only live-API harness scripts requiring credentials — standing block). Deterministic probes executed at pin: `grep -n '@app.post("/jira")' sweepai/api.py` → :296 only, and the route line carries NO dependencies=[...] (contrast :284 GitHub route with Depends(validate_signature)); `grep -n 'target=handle_jira_ticket' sweepai/api.py` → :301 only; `grep -rn 'handle_jira_ticket' sweepai/` → import api.py:56, def on_jira_ticket.py:27, thread target api.py:301 (single entry point); `grep -n 'repo:\\s\*' sweepai/handlers/on_jira_ticket.py` → :10 only; `grep -n '# wait for this' sweepai/handlers/on_jira_ticket.py` → :48 only; `grep -n 'create_issue(title=title' sweepai/handlers/on_jira_ticket.py` → :46 only; `grep -n 'except' sweepai/handlers/on_jira_ticket.py` → ZERO matches (no error handling in the module); `grep -n 'get_page(0)' sweepai/handlers/on_jira_ticket.py` → :74 only; `grep -n 'basic_auth=' sweepai/handlers/on_jira_ticket.py` → :22 only; `grep -n 'Fixes #' sweepai/handlers/on_jira_ticket.py` → :77 (literal f-string marker read, third reader of the "Fixes #N.\n" contract).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "jira_webhook handle_jira_ticket create_issue Fixes marker add_comment", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// api.py:276-303, on_jira_ticket.py (86L whole) at pin substituted — see verification.md pass 5.
```

## Verdict
Adopt the mirroring pattern as the multi-forge answer: convert the foreign tracker's object into your native issue object BEFORE the pipeline starts, so all downstream machinery (progress UI, PR assembly, marker contract, cron maintenance) stays single-forge; adopt the detached-thread + immediate-200 webhook posture (the tracker's retry semantics must not see your long job); and adopt the post-completion marker-based result discovery (find the artifact by its body contract, not by API correlation fields). Adapt: put a signature or token gate on the second-forge route (Sweep ships it wide open); log the silent-return paths (missing repo binding, no PR found) — Sweep gives the reporter nothing; add dedup/latest-wins keyed on the foreign issue key before spawning threads; gate the PR scan on bot login like delete_old_prs does; wrap the worker body so failures reach the foreign tracker as a comment. Omit: the credential re-fetch dance mid-function (re-fetching the client after on_ticket is only needed if the pipeline invalidates tokens — verify before porting), and basic_auth with an API token as the password (use the tracker's native token auth header). Coverage caveat: no live direct test at pin; the route is unauthenticated, so this capsule doubles as a security review note for any port.
