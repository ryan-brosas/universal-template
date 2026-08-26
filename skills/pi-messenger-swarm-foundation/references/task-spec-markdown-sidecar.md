<!-- capsule-v2 -->
# Task spec markdown sidecar — why do tasks carry BOTH an event log and a separate .md file?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the split of truth between `tasks/<session>.jsonl` and `tasks/<session>/<taskId>.md`?

## Log = state machine; md = human/agent-readable spec body
**Path/Symbol:** `swarm/task-store/persistence.ts:writeTaskSpec` (:22-36), `readTaskSpec` (:38-46), `deleteTaskSpec` (:48-54), path helpers (:8-20); consumers `commands.ts:createTask` (:50-51), `deleteTask` (:237-248), `queries.ts:getTaskSpec` (:180-182).
**Signature:** `writeTaskSpec(cwd, sessionId, taskId, title, content?): void`.
**Data Shape:** file body: `# <title>\n\n<content>\n` or `# <title>\n\n*Spec pending*\n` when content empty/whitespace; session ids sanitized `[^\w.-] → '_'`.

### Decisive source
```ts
fs.writeFileSync(specPath,
  content?.trim() ? `# ${title}\n\n${content.trim()}\n` : `# ${title}\n\n*Spec pending*\n`,
  'utf-8');
```
```ts
// deleteTask: remove spec file FIRST, then archive (event) to mark deleted
deleteTaskSpec(cwd, sessionId, taskId);
archiveTask(cwd, sessionId, taskId);
```

**Flow:** create writes the event THEN overwrites the spec file (spec is derived display data, not state); task.show renders spec via readTaskSpec with `*No spec*` fallback; delete unlinks the spec but keeps the archived event so history remains replayable. Progress notes live ONLY in the log (`task.progress.md` naming in README refers to progress_log rendering).
**Invariant:** The jsonl is the single source of truth — deleting or corrupting a spec md never changes status/claims; regenerating is always possible from created-payload content. Sanitization of session id happens identically in both stores' path builders, keeping them siblings under tasks/.
**Probe:** direct test coverage via router suites (`tests/swarm/router.test.ts::supports task create/claim/done end-to-end` exercises spec write+read); `grep -c "Spec pending" swarm/task-store/persistence.ts` (=1); `grep -n "replace(/[^\\\\w.-]/g" swarm/task-store/persistence.ts swarm/spawn.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "writeTaskSpec readTaskSpec getTasksJsonlPath taskSpecPath deleteTaskSpec", limit: 5 });
```

## Verdict
Adopt event-log-as-truth with disposable rendered sidecars; adapt the md template; keep delete-ordering (unlink sidecar before tombstone event) if your readers dislike ghost specs.
