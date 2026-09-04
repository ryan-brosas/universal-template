<!-- capsule-v2 -->
# Task ID minting — why are background-task IDs random 36-alphabet strings instead of counters or UUIDs?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How are task IDs generated, what does the prefix encode, and what security property does the alphabet choice carry?

## Prefixed base-36 IDs sized against symlink brute force
**Path/Symbol:** `src/Task.ts:87-106`: `TASK_ID_PREFIXES`, `getTaskIdPrefix`, `TASK_ID_ALPHABET`, `generateTaskId`; parallel copy `src/tasks/LocalMainSessionTask.ts:73-82`: `generateMainSessionTaskId`.
**Signature:** `generateTaskId(type: TaskType): string`.
**Data Shape:** 9-char id = type prefix + 8 chars from `'0123456789abcdefghijklmnopqrstuvwxyz'` via `randomBytes(8)[i] % 36`. Prefixes: `b` local_bash (kept for backward compatibility with persisted session state), `a` local_agent, `r` remote_agent, `t` in_process_teammate, `w` local_workflow, `m` monitor_mcp, `d` dream; unknown type falls back to `'x'`.

### Decisive source
```ts
// Case-insensitive-safe alphabet (digits + lowercase) for task IDs.
// 36^8 ≈ 2.8 trillion combinations, sufficient to resist brute-force symlink attacks.
const TASK_ID_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz'
export function generateTaskId(type: TaskType): string {
  const prefix = getTaskIdPrefix(type)
  const bytes = randomBytes(8)
  let id = prefix
  for (let i = 0; i < 8; i++) {
    id += TASK_ID_ALPHABET[bytes[i]! % TASK_ID_ALPHABET.length]
  }
  return id
}
```

**Flow:** every spawn site calls generateTaskId (or reuses an existing runtime id like ShellCommand's TaskOutput taskId / the agent's agentId) → the id becomes the AppState.tasks key AND the on-disk output-file name (`getTaskOutputPath(id)`), so ID space and filesystem namespace coincide.
**Invariant:** The ID must be unguessable because it names a file path that untrusted code can observe (`/tmp`-style output files + symlink init). Sequential counters would let any local process pre-create a symlink at the next predictable path and redirect task output. Main-session tasks duplicate the generator with prefix `'s'` rather than importing Task.ts's version — keep both if you port both callers, but note the drift risk.
**Probe:** `grep -n "resist brute-force symlink" src/Task.ts` (:86) and `grep -n "Keep as 'b' for backward" src/Task.ts` (:88) and `grep -cn "bytes\[i\]! % TASK_ID_ALPHABET.length" src/tasks/LocalMainSessionTask.ts` (1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "generateTaskId", limit: 5 });
```

## Verdict
Adopt the entropy argument verbatim (random IDs naming shared-namespace files). Adapt prefix letters to your task taxonomy. Omit the duplicated main-session generator by extracting it — upstream shipped the duplication first.
