<!-- capsule-v2 -->
# checkpoint-before-mutating-dispatch — why do only some tool cases save a shadow checkpoint, and how often?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Where in the agent loop is the pre-mutation checkpoint taken, and what guarantees it happens exactly once per streamed response even when several mutating tools run back-to-back?

## checkpointSaveAndMark — dispatch-side, per-API-request once-latch
**Path/Symbol:** `src/core/assistant-message/presentAssistantMessage.ts:checkpointSaveAndMark` (957–967); call sites :653 (write_to_file), :668 (apply_diff), :677 (edit/search_and_replace), :685 (search_replace), :693 (edit_file), :701 (apply_patch), :780 (new_task), :818 (generate_image); latch reset at `src/core/task/Task.ts:2696–2705`.
**Signature:** `async function checkpointSaveAndMark(task: Task): Promise<void>` guarding `await task.checkpointSave(true)`.
**Data Shape:** no inputs beyond the Task; the observable state is one boolean `currentStreamingDidCheckpoint` declared false at Task.ts :338 and reset alongside ALL other streaming latches at the start of each new API request.

### Decisive source
```ts
async function checkpointSaveAndMark(task: Task) {
    if (task.currentStreamingDidCheckpoint) {
        return
    }
    try {
        await task.checkpointSave(true)
        task.currentStreamingDidCheckpoint = true
    } catch (error) {
        console.error(`[Task#presentAssistantMessage] Error saving checkpoint: ${error.message}`, error)
    }
}
```

**Flow:** switch case for a MUTATING tool → `checkpointSaveAndMark(cline)` runs BEFORE `tool.handle(...)` → first call in the current API request snapshots and sets the latch → every later mutating tool in the SAME response skips (latch true) → latch cleared with the rest of the streaming state when the next request begins.
**Invariant:** (1) The checkpoint belongs to the DISPATCHER, not the tools: read/perception tools (read_file, list_files, search_files, codebase_search, read_command_output), interaction tools (ask_followup_question, attempt_completion, switch_mode, skill, update_todo_list) take NO checkpoint here — the taxonomy is "can this tool change the workspace or fork task state" (new_task, generate_image count as yes). (2) Exactly ONE checkpoint per API response regardless of how many mutating tools run: the once-latch makes N edits cost one snapshot while still guaranteeing every mutation batch is preceded by a restore point. (3) Checkpoint FAILURE must not block execution: the catch logs to console only — a broken checkpoint backend degrades to "no undo point", never to "tool refused". (4) Ordering is strictly before `handle`, so an approval-denied write still produced its pre-state snapshot (harmless; the snapshot predates any disk change).
**Probe:** runner BLOCKED (no node_modules/vitest; dispatch-site has no dedicated spec at pin). Deterministic source pins from repo root: `grep -c 'currentStreamingDidCheckpoint' src/core/assistant-message/presentAssistantMessage.ts` → 1; `grep -c 'checkpointSaveAndMark(cline)' src/core/assistant-message/presentAssistantMessage.ts` → 8; `grep -n 'currentStreamingDidCheckpoint = false' src/core/task/Task.ts` → lines 338 and 2698.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "checkpointSaveAndMark presentAssistantMessage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dispatcher-owned pre-mutation checkpointing with a per-request once-latch and log-only failure. Adapt which tools count as mutating to your host's toolset and where the latch resets in your loop lifecycle. Omit the VS Code shadow-git mechanics themselves (see shadow-checkpoints + checkpoint-exclude-families for that kernel). Coverage caveat: no direct spec pins this helper at HEAD; behavior pinned by whole-file source read of the switch + byte-exact greps + live graph retrieval.
