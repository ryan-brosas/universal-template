<!-- capsule-v2 -->
# Prompt-hook context compiler — how does a UserPromptSubmit hook decide, with zero LLM calls, what context to inject and at what cadence?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when every user prompt is a chance to prefetch memories or nudge capture behavior, how does a shell hook compile deterministic signals into ONE context block without ever blocking or repeating itself?

## on_user_prompt.sh — detectors → cadence → single jq emission
**Path/Symbol:** `integrations/mem0-plugin/scripts/on_user_prompt.sh` (228L; wired by hooks.json UserPromptSubmit, timeout 8).
**Signature:** stdin JSON `{prompt, session_id, cwd, transcript_path}` → stdout `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":$ctx}}` (only when ctx non-empty); always exit 0.
**Data Shape:** cross-process state lives in /tmp files keyed by `$USER`: `mem0_msg_count_$USER` (incremented every substantial prompt), `mem0_rubric_${SESSION_ID}` (once-ever rubric flag), `mem0_session_stats_$USER.json` (reads `.adds`), `mem0_session_id_$USER` (session-id fallback).

### Decisive source
```bash
# Intentionally omit -e so the script always exits 0 even if jq fails --
# must never block the user's prompt.
set -uo pipefail
...
# Auto-capture: directly call mem0 API in background every 3rd message.
# At MSG_COUNT=3 the 3rd response isn't in the transcript yet (hook fires
# before Claude responds), so we capture 4 exchanges instead of 3. The
# overlapping window ensures the next batch (MSG_COUNT=6) picks up the
# exchange that was incomplete in the previous batch.
if [ "${MEM0_AUTO_SAVE:-true}" != "false" ] && [ $((MSG_COUNT % 3)) -eq 0 ] && ...
  python3 "$SCRIPT_DIR/auto_capture.py" "$TRANSCRIPT_PATH" 2>/dev/null &
fi
```
Sections accumulate into `_PROMPT_CTX` via the join idiom `_PROMPT_CTX="${_PROMPT_CTX:+${_PROMPT_CTX}\n}<next>"` and are emitted once.

**Flow:** prompt < 20 chars → exit silently. Else increment msg-count file. Grep detectors (no API): `HAS_ERROR` (Traceback/panic:, ^fatal:, or ≥2 of Error:/Exception:/FAIL:), `FILE_PATHS` (code-extension regex, head -5), `HAS_RESUME` ("where did we leave off"-family), `HAS_REMEMBER` ("remember this"-family) — each also fires background telemetry flags. Resume lane runs two targeted searches (`session_state` top_k=3 + `decision` top_k=3) merged seen-set-dedup by memory id; otherwise prefetch lane searches the raw prompt top_k=5 (skipped when `MEM0_PREFETCH=false`). Rubric injected only while `/tmp/mem0_rubric_${SESSION_ID}` is absent, then `touch`ed (session id ladder: stdin → session-id file → `default_${USER}`). Nudges: %5 messages → store-learnings reminder; when `session_stats .adds < MSG_COUNT/3` → agent-store nudge (mechanical capture falling behind conversation volume). Every %3 with transcript + `MEM0_AUTO_SAVE!=false` → background `auto_capture.py`. No-API-key path still emits detections-only context.
**Invariant:** the hook must NEVER block a prompt: no `-e`, every command failure degrades to empty output, exit 0 always. The full search rubric is once-per-session (flag file), not per-prompt. Auto-capture batches deliberately OVERLAP (4 exchanges per 3-message stride) because the hook precedes the assistant reply — a non-overlapping window would permanently lose one exchange per batch.
**Probe:** `integrations/mem0-plugin/tests/test_rubric_dedup.py` — subprocess-runs the real bash hook twice with `MEM0_RUBRIC_DIR` pointed at tmp; first substantial prompt must contain the rubric ("Mem0 searches apply", "metadata.type"), second must print nothing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "mem0", query: "user prompt rubric cadence message count gate", limit: 10 });
```
Executed live: surfaces `tests/test_rubric_dedup.py` fixtures/tests and sibling detector tests; the bash script itself has no Function nodes (parse-partial).

## Verdict
Adopt the compiler shape: cheap local detectors → cadenced nudges from tiny /tmp state files → one atomic additionalContext emission; adopt the overlapping-window reasoning for any pre-response capture cadence and once-per-session gating for instructional text. Adapt thresholds (20-char floor, %3/%5 strides, adds<msg/3 ratio). Omit mem0-specific query strings. Coverage caveat: tree-sitter marks lines 104,177,182,186,191,195,216 parse-partial (all `${VAR:+${VAR}\n}` joins); those exact ranges were read directly from source this pass and carry the join semantics claimed here.
