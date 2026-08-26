<!-- capsule-v2 -->
# Swarm protocol prompt sandwich — what text turns a generic coding agent into a compliant swarm worker?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** Which prompt clauses are contract-critical when porting the subagent bootstrapping?

## System prompt = role+persona+mission+context+protocol; user prompt = mission+procedure+DoD
**Path/Symbol:** `swarm/spawn.ts:buildSwarmProtocol` (:171-186), `buildSystemPrompt` (:188-214), `buildPrompt` (:216-256).
**Signature:** `buildSystemPrompt(request: SpawnRequest): string`; protocol appended verbatim to BOTH authored and `--agent-file` spawns (:469).
**Data Shape:** 10 numbered protocol clauses; system tmpfile written `0o600` under mkdtemp and passed via `--append-system-prompt`.

### Decisive source
```ts
'3. Task claiming is required: ... Failure to claim indicates another agent owns it; report the conflict and await further instruction.',
"5. Progress updates are required: Update task progress every 3-5 tool calls or at significant milestones...",
'6.5 Report findings IN the task.done summary or task.progress messages — not just in your response text. The coordinator reads your output via `pi-messenger-swarm task show <taskId>`...',
'9. Check channel feed between turns: ... This is pull-based: nobody pushes messages to you.',
'10. Exit immediately after marking task done: `bash({ command: "exit 0" })`. Do not stay alive after your mission is complete.'
```
plus the coordinator-side rule injected at registration:
```
Key: when you spawn agents for tasks, delegate the work — do NOT claim those tasks yourself
(spawned agents claim and execute them). Only claim tasks you will implement personally.
```
(`index.ts:sendRegistrationContext` :153-165.)

**Flow:** objective resolution order is `request.objective ?? request.message` trimmed; persona rides only into the system prompt; taskId adds an "Assigned Task" block AND switches the user prompt to include the three-step claim/progress/done procedure with literal command templates. The pull-based clause (9) is what makes feed-only messaging work — nothing ever pushes to a worker.
**Invariant:** Clause 6.5 + the coordinator context line form ONE ownership loop: findings must live in the task record because the coordinator reads `task show`, not chat; delegation-not-claiming prevents parents from racing their own children (also enforced softly by the claim-time warning). Dropping clause 10 leaves zombie workers burning tokens post-mission.
**Probe:** `grep -c "Exit immediately after marking task done" swarm/spawn.ts` (=1); direct test `tests/swarm/spawn-system-prompt.test.ts::appends swarm protocol to agent-file system prompt` (title grep: `grep -n "swarm protocol" tests/swarm/spawn-system-prompt.test.ts`); `grep -c "do NOT claim those tasks yourself" index.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "buildSwarmProtocol buildSystemPrompt buildPrompt sendRegistrationContext", limit: 6 });
```

## Verdict
Adopt the protocol-clause set (claim-before-work, cadence-bounded progress, evidence-in-record, pull-based feed reading, exit-on-done) and the parent-side delegate-don't-claim rule verbatim as behavioral contracts; adapt command spellings; omit persona plumbing if you don't use role-play.
