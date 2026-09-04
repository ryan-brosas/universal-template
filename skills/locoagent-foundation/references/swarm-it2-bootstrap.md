<!-- capsule-v2 -->
# it2 bootstrap ladder — how is a Python CLI tool installed safely and verified against the real API?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what does installing the `it2` CLI require beyond running a package manager, and how do you detect the "Python API disabled" case specifically?

## Package-manager preference + homedir-cwd install + API-aware verification
**Path/Symbol:** `src/utils/swarm/backends/it2Setup.ts:detectPythonPackageManager` (:40-72), `installIt2` (:90-144), `verifyIt2Setup` (:152-195), `setPreferTmuxOverIterm2` (:229-238), `getPreferTmuxOverIterm2` (:243-245).
**Signature:** `detectPythonPackageManager(): Promise<'uvx'|'pipx'|'pip'|null>` (preference order; pip3 maps to 'pip').
**Data Shape:** `It2VerifyResult = { success, error?, needsPythonApiEnabled? }` — the tri-state drives which UI instructions show.

### Decisive source
```ts
// Run from home directory to avoid reading project-level pip.conf/uv.toml
// which could be maliciously crafted to redirect to an attacker's PyPI server
result = await execFileNoThrowWithCwd('uv', ['tool', 'install', 'it2'], { cwd: homedir() })
```
```ts
// Try to list sessions - this tests the Python API connection
if (result.code !== 0) {
  const stderr = result.stderr.toLowerCase()
  if (stderr.includes('api') || stderr.includes('python') ||
      stderr.includes('connection refused') || stderr.includes('not enabled')) {
    return { success: false, error: 'Python API not enabled in iTerm2 preferences',
             needsPythonApiEnabled: true }
  }
```

**Flow:** detection probes `which uv|pipx|pip|pip3` in preference order → install runs from `$HOME` with `--user`/tool-isolated modes (no sudo) → verify re-runs `it2 session list` (the REAL dependency — the Python API) and classifies stderr into needsPythonApiEnabled vs generic failure → success persists two config booleans: `iterm2It2SetupComplete` (skip prompt next time) and optionally `preferTmuxOverIterm2=true` when the user declines setup — the boolean that registry.ts's detection ladder reads to suppress `needsIt2Setup`.
**Invariant:** package installation must not honor project-local config files (supply-chain guard); verification must exercise the deepest dependency (API), not mere binary existence; user refusal is itself persisted state so prompts never nag.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'maliciously crafted' src/utils/swarm/backends/it2Setup.ts` (:96); `grep -n 'needsPythonApiEnabled' src/utils/swarm/backends/it2Setup.ts | head -2` (:31/:181).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "installIt2 verifyIt2Setup detectPythonPackageManager setPreferTmuxOverIterm2", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt hardened-cwd tool installation plus capability-verifying setup checks and refuse-option persistence; adapt manager names; omit iTerm-specific instruction text.
