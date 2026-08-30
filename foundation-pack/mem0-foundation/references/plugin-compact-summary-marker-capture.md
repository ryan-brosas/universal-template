<!-- capsule-v2 -->
# Post-compact summary capture — why can't the PreCompact hook capture the summary, and what replaces run_id dedup for a once-per-session capture?

**Source:** mem0 Apache-2.0 `main@7e096155714c`. **Question:** when the artifact you want to store (the compaction summary) does not exist yet at hook-fire time, how do you capture it later without double-storing on resume?

## Marker-file once-capture (capture_compact_summary.py)
**Path/Symbol:** `integrations/mem0-plugin/scripts/capture_compact_summary.py:find_compact_summary` (lines 70–95) + `store_summary` (97–143) + `main` (145–190); wired by `scripts/on_session_start.sh` lines 199–202 (`source=compact` branch) — NOT by `on_pre_compact.sh`.
**Signature:** `find_compact_summary(lines: list[str]) -> str`; `store_summary(api_key, summary, user_id, session_id, project_id="", branch="", cwd=None) -> bool`.
**Data Shape:** `MAX_TAIL_LINES = 2000` (≈8MB window at 4096 B/line), `MAX_SUMMARY_CHARS = 50000`, `COMPACT_SUMMARY_EXPIRY_DAYS = 90`; POST /v3/memories/add/ with `messages=[{"role":"assistant","content":summary}]`, `infer=True`, metadata `{type:"compact_summary", source:"session-start-compact", session_id}` (+branch), `expiration_date=today+90d`, body merged with `load_instructions(cwd)`.

### Decisive source
```python
    marker_dir = os.path.expanduser("~/.mem0")
    marker_file = os.path.join(marker_dir, f"compact_captured_{session_id}")
    if session_id and os.path.isfile(marker_file):
        log.info("Compact summary already captured for session %s — skipping", session_id)
        return
```
and the role comment that pairs with the Stop-hook capsule:
```python
    # The compact summary is model-authored prose, in the first person and with no
    # framing to mark it as such. Under role="user" mem0 reads "I recommend X" as
    # the human saying it and stores "User recommends X".
```
**Flow:** PreCompact (`on_pre_compact.sh`) fires BEFORE the summary exists — it can only stash stdin to `/tmp/mem0_precompact_input_$$.json` and background `on_pre_compact.py --source=pre-compaction` (session_state capture; pass-8 capsule). The compact-summary text is captured at the NEXT SessionStart with `source=compact`: same hook input piped to this script → tail-read 2000 transcript lines → reverse walk for newest entry with `isCompactSummary: true` (content may be a plain string or a block list; text blocks concatenated) → gate: stripped length ≥ 100 chars → marker-file check → store → write empty marker file ONLY on success.
**Invariant:** the marker FILE replaces `run_id` infer-dedup here because the capture is once-per-session, not self-updating: SessionStart(compact) can fire repeatedly (resume after compaction chains), and re-running infer would fork duplicate summaries rather than converge. The marker is written only AFTER a 200/201, so a failed store retries next start. The speaker-role rule is the same attribution bug as the Stop hook (test_message_roles.py pins both); the ≥100-char gate here reads the STRIPPED summary (the Stop hook's gate reads raw — different order, same purpose).
**Probe:** `integrations/mem0-plugin/tests/test_message_roles.py:test_compact_summary_posts_assistant_prose_as_assistant` — monkeypatches urlopen, asserts the assistant prose lands under `role="assistant"`. Executed GREEN this pass (4 passed in the file). Byte-exact grep probes: `compact_captured_{session_id}` (1 hit), `isCompactSummary` (3 hits in this file), `--source=pre-compaction` in on_pre_compact.sh (1 hit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "capture compact summary isCompactSummary marker", limit: 10, fields: ["signature", "lines"] });
```
Recorded for graph-connected sessions; MCP not connected this pass (DEGRADED path, whole-file direct reads + executed tests instead).

## Verdict
Adopt the split "PreCompact = stash state, next SessionStart = harvest artifact" pattern and the success-only marker file whenever a hook wants an artifact that a prior hook's event precedes. Adapt expiry (90d) and the marker directory to your host. Omit the mem0 endpoint/auth shape. Coverage: whole file read; direct test executed GREEN; wrapper chain read (on_pre_compact.sh 23 lines, on_session_start.sh compact branch).
