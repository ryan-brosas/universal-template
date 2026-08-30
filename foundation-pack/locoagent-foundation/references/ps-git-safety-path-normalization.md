<!-- capsule-v2 -->
# PS git-safety path normalization — how do you detect writes to hooks/, HEAD/, .git/ when PowerShell accepts backticks, provider prefixes, 8.3 names, and unicode dashes?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What canonicalization ladder turns arbitrary PS argument text into a comparable git-internal path, and which two guards consume it?

## normalizeGitPathArg ladder + cwd-reentry resolution feeding two predicates
**Path/Symbol:** `src/tools/PowerShellTool/gitSafety.ts`:`normalizeGitPathArg` (:48-87), `resolveCwdReentry` (:23-38), `resolveEscapingPathToCwdRelative` (:106-122), `isGitInternalPathPS` (:139-151), `isDotGitPathPS` (:158-176); consumers `powershellPermissions.ts` GIT_SAFETY_WRITE_CMDLETS/GIT_SAFETY_ARCHIVE_EXTRACTORS decisions (:70-112, :1168-1257).
**Signature:** `function isGitInternalPathPS(arg: string): boolean`; `function isDotGitPathPS(arg: string): boolean`.
**Data Shape:** In: raw arg text (Extent-preserved quotes/backticks/dashes). Internal: posix-normalized lowercase path. Out: boolean.

### Decisive source
```ts
s = s.replace(/^(?:[A-Za-z0-9_.]+\\\\){0,3}FileSystem::/i, '') // provider prefix
s = s.replace(/^[A-Za-z]:(?![\/\\\\])/, '')   // drive-relative C:foo, NOT C:\\foo
// Win32 CreateFileW per-component: strip trailing spaces then dots,
// stopping if the result is `.` or `..`
s = s.split('/').map(c => { /* iterative space+dot strip */ }).join('/')
s = posix.normalize(s)
```

**Flow:** structural strips first (unicode-dash + `/` parameter prefix with colon-bound value extraction, surrounding quotes, backtick escapes, `FileSystem::` provider prefix up to 3 dotted namespace segments, drive-relative colon) → per-component NTFS trailing-space/dot strip (`hooks .` → `hooks`; `...` → `.`) → posix.normalize → case-fold → match `{head, objects, refs, hooks}` prefixes / `.git*` incl. GIT~1 8.3 short names. Escaping forms (`../x`, absolute, drive-colon) get a SECOND chance: resolve against real cwd — if they land BACK inside cwd at a git-internal spot (`..\project\HEAD`), fire anyway; genuinely external paths return null (path-validation's business).
**Invariant:** The cwd-resolution guard is SOLE protection for the bare-repo `HEAD` attack because path-validation deliberately excludes bare `HEAD` (false positives on legit files named HEAD) — removing it reopens planted-HEAD hook execution. Consumers split by ambiguity: `hooks/`-style prefixes only matter when a git subcommand coexists (plus archive-extractor TOCTOU ask since tar contents are opaque), while `.git/` writes ask unconditionally (a planted `.git/hooks/pre-commit` fires on the user's NEXT commit with no git in this command).
**Probe:** `grep -nF "resolveEscapingPathToCwdRelative" src/tools/PowerShellTool/gitSafety.ts | wc -l` → `3` and `grep -nF "'head', 'objects', 'refs', 'hooks'" src/tools/PowerShellTool/gitSafety.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "normalizeGitPathArg resolveEscapingPathToCwdRelative", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered normalization ladder (structural strips BEFORE NTFS per-component strips BEFORE normalize BEFORE case-fold) and both predicates with their different consumer gating. Adapt prefix lists to your VCS. Omit Windows shell lore. Coverage caveat: probes deterministic; graph confirms both functions :48-87/:106-122 line-exact rank#1.
