<!-- capsule-v2 -->
# Remote-agent restore & sidecar persistence — how do remote tasks survive process restarts without persisting status?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is stored in the session sidecar, what is fetched fresh on resume, and which error classes drop vs keep a restored task?

## Identity-only sidecar; 404/archived drop, auth errors keep; pollStartedAt resets the review clock
**Path/Symbol:** `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:477-532`: `restoreRemoteAgentTasks`(+Impl); :92-111 `persistRemoteAgentMetadata`/`removeRemoteAgentMetadata`; :386-466 `registerRemoteAgentTask`.
**Signature:** `restoreRemoteAgentTasks(context: TaskContext): Promise<void>` (never throws — outer catch logs).
**Data Shape:** sidecar record = taskId, remoteTaskType, sessionId, title, command, spawnedAt, toolUseId, isUltraplan, isRemoteReview, isLongRunning, remoteTaskMetadata. NO status field ("Status is not stored — it's fetched fresh from CCR on restore"). RemoteTaskType union: `'remote-agent'|'ultraplan'|'ultrareview'|'autofix-pr'|'background-pr'`.

### Decisive source
```ts
} catch (e) {
  // Only 404 means the CCR session is truly gone. Auth errors (401,
  // missing OAuth token) are recoverable via /login — the remote
  // session is still running. fetchSession throws plain Error for all
  // 4xx (validateStatus treats <500 as success), so isTransientNetworkError
  // can't distinguish them; match the 404 message instead.
  if (e instanceof Error && e.message.startsWith('Session not found:')) {
    void removeRemoteAgentMetadata(meta.taskId)
  } else { /* recoverable — skip but KEEP sidecar */ }
  continue
}
if (remoteStatus === 'archived') {
  // Session ended while the local client was offline. Don't resurrect.
  void removeRemoteAgentMetadata(meta.taskId)
```

**Flow:** on --resume (after switchSession so the sidecar dir points at the resumed session) → list sidecar entries → fetchSession each → archived or message-404 ⇒ delete entry; recoverable errors ⇒ skip, keep entry → else rebuild state (`startTime: meta.spawnedAt`, fresh `pollStartedAt: Date.now()`) and restart polling. registerRemoteAgentTask creates the output file BEFORE registering ("uses appendTaskOutput(), not TaskOutput, so the file must exist for readers before any output arrives") and fire-and-forget persists identity — "persistence failures must not block task registration".
**Invariant:** Restoring `pollStartedAt` from scratch is deliberate: review-timeout clocks run from LOCAL observation start "so a restore doesn't immediately time out a task spawned >30min ago". Unknown persisted remoteTaskType values degrade to 'remote-agent' via isRemoteTaskType rather than failing registration.
**Probe:** `grep -n 'immediately time out' src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` (:38) and `grep -n 'Session not found:' src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` (:498) and `grep -c 'must not block task registration' src/tasks/RemoteAgentTask/RemoteAgentTask.tsx` (1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "restoreRemoteAgentTasks", limit: 5 });
```

## Verdict
Adopt identity-only persistence + error-class disposition verbatim. Adapt sidecar location to your session store. Omit ultraplan/ultrareview metadata fields if you carry only generic remote agents.
