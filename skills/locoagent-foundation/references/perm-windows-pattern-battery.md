<!-- capsule-v2 -->
# Windows path-pattern detection — detect-don't-normalize against canonicalization bypasses

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you stop a path like `GIT~1`, `.git.`, `.git.CON`, or `file.txt::$DATA` from slipping past string-matching security checks — and why detect instead of normalize?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/filesystem.ts` — `hasSuspiciousWindowsPathPattern` (:545-610), design-rationale docstring (:498-544); `src/utils/permissions/pathValidation.ts` — `validatePath` shell-expansion + tilde-variant rejections (:373-485), `isPathAllowed` mirror ladder (:141-263), `isDangerousRemovalPath` collapsed-separator drive checks (:331-367), `isPathInSandboxWriteAllowlist` outside-working-dir-only (:101-123).
**Signature:** `hasSuspiciousWindowsPathPattern(path: string): boolean`.
**Data Shape:** Detected classes: NTFS ADS colon (position >2, Windows/WSL only — Linux/macOS access ADS via xattrs so colons stay legal), 8.3 short names (`~\d`), long-path/device prefixes (`\\?\`, `\\.\`, `//?/`, `//./`), trailing dots/spaces (`[.\s]+$`), DOS device suffixes (`.(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$`), ≥3-dot path components, UNC (`containsVulnerableUncPath`).

### Decisive source
```text
## Why Detection Instead of Normalization?
1. Filesystem dependency: Short path normalization is relative to files that
   currently exist ... 2. Race conditions: filesystem state can change between
   normalization and actual file access (TOCTOU) ... 4. Reliability: Pattern
   detection is more predictable and doesn't depend on external system state.
```

**Flow:** every candidate path (original AND symlink-resolved forms) runs the pattern battery → any hit = manual approval required, never auto-normalized → on ALL platforms (NTFS mounts exist on Linux/macOS via ntfs-3g; only the ADS colon check is platform-gated). Downstream in pathValidation: shell-expansion metachars (`$`, `%`, leading `=` for zsh equals-expansion) are rejected because validation sees literals while the shell expands at execution (TOCTOU); unhandled tilde variants (`~root`, `~+`, `~-`) likewise; glob patterns are banned outright in write/create operations and validated via BASE directory for reads; removal safety collapses separator runs first so PowerShell's `C:\\Windows` cannot dodge the drive-child check.

**Invariant:** (1) Detection over normalization is a stated security posture — normalizing 8.3 names requires files to EXIST and races the filesystem; AppSec sign-off documented in-source. (2) The three-consecutive-dots check requires separators on both sides so Next.js catch-all routes `[...name]` stay legal. (3) Sandbox write-allowlist paths count ONLY outside the working dir — the allowlist always seeds `.` (cwd), which would otherwise bypass the acceptEdits gate at step 3 of isPathAllowed. (4) Deny-within-allow is honored inside sandbox config resolution (deny rules beat parent allows after symmetric symlink resolution).

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF 'AppSec first' src/utils/permissions/filesystem.ts` → :540; `grep -nF '/(^|\/|\\)\.{3,}(\/|\\|$)/' src/utils/permissions/filesystem.ts` → :598; `grep -nF 'bypass the acceptEdits gate at step 3' src/utils/permissions/pathValidation.ts` → :232; graph search `validatePath` → pathValidation.ts :373-485 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "hasSuspiciousWindowsPathPattern isDangerousRemovalPath validateGlobPattern", limit: 8 });
```

## Verdict
Adopt the pattern battery verbatim (it is platform-table-driven) plus reject-on-shell-metachar for any path that a shell will later reinterpret. Adapt device-name lists as Windows evolves. Omit WSL-specific colon handling if your host never mounts DrvFs.
