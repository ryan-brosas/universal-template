<!-- capsule-v2 -->
# agentMdExcludes symlink-proof matching — how does a settings-driven memory-file exclude list match reliably when symlinks make user-written patterns and real paths disagree?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you implement "never load these AGENT.md files" excludes so `/tmp/project/AGENT.md` still matches when macOS resolved the session cwd to `/private/tmp/project/…`?

## isAgentMdExcluded + resolveExcludePatterns: match BOTH the written path and its realpath-resolved twin
**Path/Symbol:** `src/utils/agentmd.ts`:`isAgentMdExcluded` (`:547-573`), `resolveExcludePatterns` (`:581-612`).
**Signature:** `isAgentMdExcluded(filePath: string, type: MemoryType): boolean`; `resolveExcludePatterns(patterns: string[]): string[]`.
**Data Shape:** Applies ONLY to `type ∈ {'User','Project','Local'}` — `Managed`, `AutoMem`, `TeamMem` are NEVER excludable (Managed is policy; AutoMem/TeamMem are separate memory systems). Patterns come from `getInitialSettings().claudeMdExcludes`. Matching is `picomatch.isMatch(normalizedPath, expandedPatterns, { dot: true })`.

### Decisive source
```ts
const normalizedPath = filePath.replaceAll('\\', '/')
// Build an expanded pattern list that includes realpath-resolved versions of
// absolute patterns. This handles symlinks like /tmp -> /private/tmp on macOS:
// the user writes "/tmp/project/AGENT.md" in their exclude, but the system
// resolves the CWD to "/private/tmp/project/...", so the file path uses the
// real path. By resolving the patterns too, both sides match.
const expandedPatterns = resolveExcludePatterns(patterns).filter(p => p.length > 0)
...
// inside resolveExcludePatterns — absolute patterns only:
const globStart = normalized.search(/[*?{[]/)      // static prefix before any glob char
const staticPrefix = globStart === -1 ? normalized : normalized.slice(0, globStart)
const dirToResolve = dirname(staticPrefix)
const resolvedDir = fs.realpathSync(dirToResolve).replaceAll('\\', '/')
if (resolvedDir !== dirToResolve) {
  const resolvedPattern = resolvedDir + normalized.slice(dirToResolve.length)
  expanded.push(resolvedPattern)                   // ADDED, not substituted
}
```

**Flow:** type gate (non-excludable types return false immediately) → load patterns; none ⇒ false → normalize backslashes to slashes on BOTH sides → expansion pass: for each ABSOLUTE pattern (glob-only patterns like `**/*.md` have no fs prefix to resolve), split off the static prefix before the first `* ? {[` character, `realpathSync` the prefix's dirname, and push a resolved CLONE alongside the original → single picomatch match over the expanded list with `{dot:true}` so dotdirs are honored.
**Invariant:** Resolved variants are ADDED to the pattern list, never substituted for the originals — which side of the pair is a symlink is environment-dependent, so testing both is the only robust posture. Resolution failure (directory doesn't exist) is silently skipped for that pattern; one bad pattern must not disable exclusion. The realpathSync call is deliberately SYNC (`:599` comment): the caller chain `processMemoryFile → getMemoryFiles` runs in sync context at that point.
**Probe:** Coverage caveat: repo ships no runnable test host here (Bun-run vitest-style suite; no direct test exercises excludes). Deterministic probe: `search_graph --project locoagent --name-pattern "^isAgentMdExcluded$"` and `"^resolveExcludePatterns$"` resolve line-exact; grep pins the backslash normalization at `src/utils/agentmd.ts:558`, the glob-char scan at `:593`, and the double-add at `:600-604`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isAgentMdExcluded resolveExcludePatterns symlink exclude", limit: 10 });
```

## Verdict
Adopt dual-variant (original + realpath-resolved) pattern matching with a type gate that makes policy memory non-excludable, and dot-aware glob matching. Adapt the settings key (`claudeMdExcludes`) and memory-type names to your host. Omit the analytics eventing. Caveat: behavior pinned by source comments + graph anchors only — no direct test ran on this host.
