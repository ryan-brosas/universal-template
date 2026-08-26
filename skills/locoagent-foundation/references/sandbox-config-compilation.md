<!-- capsule-v2 -->
# Sandbox settings-to-runtime config compiler — which paths/domains does the OS sandbox actually get told to allow and deny?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do Claude-style permission rules and `sandbox.*` settings compile into one concrete SandboxRuntimeConfig, without a settings path convention silently widening or narrowing the OS-level fence?

## Settings→config compilation
**Path/Symbol:** `src/utils/sandbox/sandbox-adapter.ts` : `convertToSandboxRuntimeConfig` (:172-384) + path resolvers `resolvePathPatternForSandbox` (:99-119) / `resolveSandboxFilesystemPath` (:138-146).
**Signature:** `(settings: SettingsJson) => SandboxRuntimeConfig` with `{ network: { allowedDomains, deniedDomains, ... }, filesystem: { denyRead, allowRead, allowWrite, denyWrite } }`.
**Data Shape:** inputs are per-source permission rule strings (`Edit(path)`, `Read(path)`, `WebFetch(domain:x)`) plus `sandbox.filesystem.{allowWrite,denyWrite,denyRead,allowRead}` arrays; output arrays feed sandbox-runtime's mount/proxy config.

### Decisive source
```ts
// Always include current directory and Claude temp directory as writable
const allowWrite: string[] = ['.', getClaudeTempDir()]
...
// SECURITY: Git's is_git_directory() treats cwd as a bare repo if it has
// HEAD + objects/ + refs/. An attacker planting these (plus a config with
// core.fsmonitor) escapes the sandbox when Claude's unsandboxed git runs.
bareGitRepoScrubPaths.length = 0
const bareGitRepoFiles = ['HEAD', 'objects', 'refs', 'hooks', 'config']
for (const dir of cwd === originalCwd ? [originalCwd] : [originalCwd, cwd]) {
  for (const gitFile of bareGitRepoFiles) {
    const p = resolve(dir, gitFile)
    try {
      statSync(p)
      denyWrite.push(p)
    } catch {
      bareGitRepoScrubPaths.push(p)
    }
  }
}
```

**Flow:** Domains first — policy `allowManagedDomainsOnly` collapses allowed domains to policySettings only (WebFetch(domain:) allow rules from user/local/flag sources ignored; DENIED domains still respected from all sources); then filesystem: seed `allowWrite` with cwd + temp dir; ALWAYS `denyWrite` every settings.json across all SETTING_SOURCES + managed drop-in dir (+ cwd `.claude/settings*.json` when user has cd'd); block `.claude/skills` AND project-root `skills/` in both original and current cwd (skills auto-load with full capability ⇒ same privilege as commands/agents); bare-repo sentinel files existing at config time → denyWrite (ro-bind in place), non-existing → scrub list; worktree main repo path (resolved once at init) appended to allowWrite for index.lock access; `--add-dir` additionalDirectories merged from settings AND bootstrap state. Per source iteration resolves each rule's path with the SOURCE-appropriate resolver.

**Invariant:** (1) TWO path grammars coexist DELIBERATELY — permission-rule content uses `//path`⇒absolute, `/path`⇒SETTINGS-DIR-relative (`resolvePathPatternForSandbox`), while `sandbox.filesystem.*` uses standard semantics `/path`⇒absolute-as-written (`resolveSandboxFilesystemPath`, issue #30067); porting one resolver over both silently re-anchors user paths. (2) The bare-repo split (exists→deny vs missing→scrub post-command) exists because unconditional denyWrite would make bwrap mount 0-byte `/dev/null` stubs at non-existent paths — leaving ghost HEAD files on the host and breaking `git log HEAD` inside the command. (3) Deny-lists must be computed per-command-refresh because they depend on live cwd state.

**Probe:** anchored at the locoagent repo root — `grep -n "allowWrite: string\[\] = \['\.', getClaudeTempDir()\]" src/utils/sandbox/sandbox-adapter.ts` → :225; `grep -n "'HEAD', 'objects', 'refs', 'hooks', 'config'" src/utils/sandbox/sandbox-adapter.ts` → :271; `grep -n 'bareGitRepoScrubPaths.length = 0' src/utils/sandbox/sandbox-adapter.ts | head -1` → :270; `grep -n "resolve(originalCwd, 'skills')" src/utils/sandbox/sandbox-adapter.ts` → :254; `grep -n "resolve(originalCwd, '.claude', 'skills')" src/utils/sandbox/sandbox-adapter.ts` → :252; `grep -n "startsWith('//')" src/utils/sandbox/sandbox-adapter.ts | head -2` → :104,:110,:144; `grep -n "cwd !== originalCwd" src/utils/sandbox/sandbox-adapter.ts | head -2` → :242,:255.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "convertToSandboxRuntimeConfig allowWrite denyWrite settings", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "resolvePathPatternForSandbox resolveSandboxFilesystemPath", limit: 5 });
```

## Verdict
Adopt the dual-grammar resolution split, the always-deny set (settings files, skills dirs, managed drop-ins), and the exists-vs-scrub bare-repo defense as a package — they were each added against a concrete escape (#30067 path anchoring, skills privilege parity, planted-bare-repo core.fsmonitor escape). Adapt domain sources to your own policy tiers. Omit ripgrep argv0 embedded-mode plumbing unless you embed rg.
