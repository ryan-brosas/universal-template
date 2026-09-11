<!-- capsule-v2 -->
# Git status snapshot — parallel reads under --no-optional-locks with bounded output and null-degrade?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** reading repo state into the system context without corrupting the user's index or hanging on huge repos.

## getGitStatus
**Path/Symbol:** `src/context.ts:getGitStatus` (:36-111), consumed by `getSystemContext` :124-128.
**Signature:** `memoize(async (): Promise<string | null>)`; five commands fan out via one `Promise.all`.
**Data Shape:** composed block: snapshot disclaimer + branch + main branch + optional git user + status (≤2000 chars) + recent commits (log -n 5).

### Decisive source
```ts
const [branch, mainBranch, status, log, userName] = await Promise.all([
  getBranch(),
  getDefaultBranch(),
  execFileNoThrow(gitExe(), ['--no-optional-locks', 'status', '--short'],
    { preserveOutputOnError: false }).then(({ stdout }) => stdout.trim()),
  execFileNoThrow(gitExe(), ['--no-optional-locks', 'log', '--oneline', '-n', '5'], ...),
  execFileNoThrow(gitExe(), ['config', 'user.name'], ...),
])
const truncatedStatus = status.length > MAX_STATUS_CHARS
  ? status.substring(0, MAX_STATUS_CHARS) +
    '\n... (truncated because it exceeds 2k characters. If you need more information, run "git status" using BashTool)'
  : status
```

**Flow:** test-env guard (avoids cycles) → `getIsGit()` gate → five READS in parallel, all with `--no-optional-locks` so inspection never takes the index lock while an editor/IDE holds or wants it → trim → hard-truncate status at 2000 chars WITH an instruction telling the model how to get more via BashTool → join with blank lines; any failure → logError + null (context simply omits the gitStatus key).
**Invariant:** read-only git inspection MUST use `--no-optional-locks` or the assistant itself becomes the thing that locks a user's repo; truncation messages double as tool-routing hints ("run it yourself with BashTool"); degraded detection (not-git, git failure) yields null not empty-string, and the caller spreads conditionally (`...(gitStatus && { gitStatus })`) so absent keys vanish from the rendered context.
**Probe:** no upstream test (coverage caveat). Deterministic probe: `grep -c "no-optional-locks" src/context.ts` → 2; truncation text pinned verbatim :85-89.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getGitStatus no-optional-locks MAX_STATUS_CHARS", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt parallel lock-free reads + hint-bearing truncation + null-degrade; adapt which fields you surface; omit diagnostics logging. Porting trap: plain `git status` from an agent can block IDEs on the index lock; unbounded status output on a monorepo silently eats the context budget on turn one.
