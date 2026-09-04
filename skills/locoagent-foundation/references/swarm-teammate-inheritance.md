<!-- capsule-v2 -->
# Teammate spawn env/flag inheritance — which parent flags and env vars must reach a tmux-spawned teammate, and which must NOT?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what is the minimal correct inheritance set for teammate processes spawned through a fresh login shell?

## buildInheritedCliFlags + TEAMMATE_ENV_VARS allowlist
**Path/Symbol:** `src/utils/swarm/spawnUtils.ts:buildInheritedCliFlags` (:38-89), `TEAMMATE_ENV_VARS` (:96-128), `buildInheritedEnvVars` (:135-146), `getTeammateCommand` (:23-28).
**Signature:** `buildInheritedEnvVars(): string` — returns an `env KEY=VALUE ...` prefix string; values shell-quoted via `quote()`.
**Data Shape:** always-on: `CLAUDECODE=1`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`; conditional forwarding ONLY when set and non-empty.

### Decisive source
```ts
// Propagate permission mode to teammates, but NOT if plan mode is required
// Plan mode takes precedence over bypass permissions for safety
if (planModeRequired) {
  // Don't inherit bypass permissions when plan mode is required
} else if (permissionMode === 'bypassPermissions' || getSessionBypassPermissionsMode()) {
  flags.push('--dangerously-skip-permissions')
}
```
```ts
// CCR marker — teammates need this for CCR-aware code paths. Auth finds
// its own way via /home/claude/.claude/remote/.oauth_token regardless;
// the FD env var wouldn't help (pipe FDs don't cross tmux).
'CLAUDE_CODE_REMOTE',
// Auto-memory gate (memdir/paths.ts) checks REMOTE && !MEMORY_DIR to
// disable memory on ephemeral CCR filesystems. Forwarding REMOTE alone
// would flip teammates to memory-off when the parent has it on.
'CLAUDE_CODE_REMOTE_MEMORY_DIR',
```

**Flow:** command template (`PaneBackendExecutor.spawn` :154): `cd <cwd> && env <inherited-env> <binary> --agent-id --agent-name --team-name --agent-color --parent-session-id [--plan-mode-required] <inherited-flags>` → CLI flag inheritance: bypass/acceptEdits (plan-mode veto first), explicit `--model` (quoted), `--settings`, per-plugin `--plugin-dir`, ALWAYS `--teammate-mode <snapshot>` so leader and teammates agree, `--chrome`/`--no-chrome` only when explicitly set → env allowlist covers provider selection (BEDROCK/VERTEX/FOUNDRY — "without these, teammates default to firstParty and send requests to the wrong endpoint" GH #23561), base URL, config dir, remote markers, and the full proxy/CA family.
**Invariant:** safety precedence (plan > bypass) is encoded in the branch order, not the caller; env forwarding is an ALLOWLIST not wholesale inheritance because tmux login shells drop the parent env selectively; FDs don't cross tmux — credentials must travel by files or env, never descriptors.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'pipe FDs don.t cross tmux' src/utils/swarm/spawnUtils.ts` (:108); `grep -n 'wrong endpoint' src/utils/swarm/spawnUtils.ts` (:98).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "buildInheritedCliFlags buildInheritedEnvVars getTeammateCommand", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt explicit inheritance allowlists with safety-first branch ordering for any child agent process; adapt the specific var names to your provider stack; omit CCR markers unless porting that runtime.
