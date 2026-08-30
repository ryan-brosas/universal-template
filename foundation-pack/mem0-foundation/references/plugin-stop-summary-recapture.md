<!-- capsule-v2 -->
# Stop-hook session summary recapture — how does a Stop hook keep ONE self-updating summary per session instead of accumulating duplicates?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when an agent-memory plugin fires a capture hook at every turn end, how does it make the stored session summary converge to the latest turn rather than pile up stale ones — and whose voice must the content be in?

## Stop-hook summary writer (capture_session_summary.py)
**Path/Symbol:** `integrations/mem0-plugin/scripts/capture_session_summary.py:store_summary` (lines 159–215) + `main` (218–264); wired by `hooks.json` Stop → `on_stop.sh`, timeout 30.
**Signature:** `store_summary(api_key: str, summary_prompt: str, user_id: str, session_id: str, project_id: str, branch: str, files: list[str], cwd: str | None = None) -> bool`.
**Data Shape:** POST `{API_URL}/v3/memories/add/` with Token auth, 15s urllib timeout; body carries top-level `user_id`/`app_id`/`run_id=session_id`, `infer=True`, `expiration_date=today+90d`, metadata `{type:"session_summary", source:"stop-hook", session_id}` (+`branch` when non-empty, +`files_touched=files[:20]` when any). Returns bool; failures log to stderr only.

### Decisive source
```python
    # summary_prompt wraps the assistant's own last message. Mem0 extracts "facts
    # about the user" from each message and role is the only signal telling it who
    # spoke, so role="user" here turns Claude's opinions into the human's stated
    # preferences ("User prefers dropping Redis...").
    body = {
        "messages": [{"role": "assistant", "content": summary_prompt}],
        "user_id": user_id,
        "app_id": project_id,
        "run_id": session_id,
        ...
        "infer": True,
```
Module docstring states the recapture contract: *"Uses run_id=session_id to scope infer dedup to the session, so the final stored summary reflects the most recent turn — not just the first."*

**Flow:** Stop fires → skip if `agent_id` present (subagents never summarize) → binary-seek tail read (`tail_lines(path, 3000)` ≈ 12MB window, errors="replace") → reverse walk for last assistant message → gate: raw stripped length ≥ 100 chars BEFORE `strip_tags()` removes `<system-reminder|private|claude-mem-context|persisted-output|system_instruction>` blocks → collect files touched (tool_use `file_path` inputs + regex over Bash commands, sorted, capped 20) → wrap in extraction prompt → POST with `run_id=session_id` → mem0's infer pipeline dedups within the run, so each later Stop rewrites the session's summary.
**Invariant:** `run_id` is the dedup scope, not a partition key here: the summary is idempotent-per-session AND self-updating. The speaker-role attribution must stay `assistant` — flipping it to `user` silently converts agent conclusions into user preferences. The ≥100-char gate reads the RAW message (before tag stripping), so a long message wrapped mostly in system tags still passes while short noise never ships. Exit is always 0 (`try main() / log.error / sys.exit(0)`).
**Probe:** `integrations/mem0-plugin/tests/test_capture_session_summary.py` — monkeypatches `urlopen` to capture the request body; pins that `metadata.files_touched` is a real JSON array encoded exactly once (regression against double-encoded escaped blobs that surfaced in Claude Code/Cursor/Codex/Antigravity) and omitted entirely when no files were touched.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "capture session summary formatting funnel stop hook", limit: 10, fields: ["signature", "lines"] });
```
Executed live: returns `capture_session_summary.store_summary` (159–215), `.main` (218–264), `.extract_files_touched` (103–135), plus the test nodes; `get_code_snippet` of `store_summary` served the body above verbatim.

## Verdict
Adopt the run_id-scoped infer-dedup pattern whenever a hook re-fires per turn (it converts a fire-every-event problem into a converging single record), the assistant-role attribution rule, and the raw-length gate before sanitization. Adapt expiry (90d here) and the metadata.type vocabulary to your host. Omit the mem0-specific endpoint/auth shape. Coverage: file fully indexed (`no_recorded_issue`), whole file read directly; no coverage caveat.
