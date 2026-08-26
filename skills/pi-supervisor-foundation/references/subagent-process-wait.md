<!-- capsule-v2 -->
# Subagent process wait — child-process census via ps with a bounded poll-and-proceed wait

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How does an extension know spawned subagents finished before analyzing, without any coupling to how they were created?

## Process-tree census, host-mechanism-agnostic
**Path/Symbol:** `src/subagent-detector.ts:24-68` (`checkChildPiProcesses`), poll :74-90 (`waitForSubagents`).
**Signature:** `waitForSubagents(checkIntervalMs=2000, timeoutMs=60000): Promise<{completed: boolean; finalStatus: SubagentStatus}>`; called with `(2000, 120000)` from index.ts.
**Data Shape:** `ps -eo ppid,pid,comm | grep -E "\bpi\b"` parsed as ppid/pid/comm triples; match condition is **direct child only**: `childPpid === process.pid && comm === 'pi'`.

### Decisive source
```ts
    // Get all pi processes with their parent PID
    // Format: ppid pid command
    const { stdout } = await execAsync(`ps -eo ppid,pid,comm | grep -E "\\bpi\\b" || true`);
    ...
      // Check if this pi process is our direct child
      // Also check for grandchildren (subagents spawning subagents)
      if (childPpid === ppid && comm === 'pi') {
        pids.push(childPid);
      }
```
PORTER TRAP: the comment says "also check for grandchildren", but the code matches ONLY direct children (`childPpid === ppid`) — grandchild processes have a different ppid and are NOT counted. The in-source comment is aspirational, not behavioral.

Poll loop (:80-86): re-census every 2s until clean or timeout; on timeout one final census decides `completed`, and the caller proceeds anyway with a warning notify ("still running after timeout, proceeding with analysis").

**Flow:** agent_settled fires → census → active subagents ⇒ UI 'waiting' + bounded poll (120s cap here) → completed ⇒ analyze; timed-out ⇒ warn + analyze regardless.
**Invariant:** The wait is bounded and analysis NEVER blocks forever on stuck children — proceeding-with-warning beats indefinite deferral. Census failure (exec error, malformed lines) degrades to `{hasActiveSubagents:false}` so analysis always happens. Windows returns empty (not implemented).
**Probe:** `grep -c "checkChildPiProcesses\|waitForSubagents(2000, 120000)" src/index.ts` → 3. Direct tests: `tests/subagent-detector.test.ts:35/:58/:78/:97/:110/:131/:143` ("detects child pi processes", "ignores non-pi processes", "ignores pi processes from other parents", "handles exec errors gracefully", "handles malformed ps output", "returns immediately when no subagents", "waits for subagents to complete").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "checkChildPiProcesses ps ppid subagent", limit: 10 });
```

## Verdict
Adopt census-plus-bounded-wait for coordinating with opaque child workloads. Adapt the process name filter and census command to your platform; keep direct-child semantics OR fix the comment when you implement true descendant walks. Omit nothing on the timeout arm — waiting indefinitely on orphaned children wedges the supervisor.
