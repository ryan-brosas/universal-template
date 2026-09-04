<!-- capsule-v2 -->
# PS validatePath hostile-form ladder — which path spellings are unresolvable at validation time, and what happens to each before the realpath?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** In what order must backtick escapes, provider separators, UNC/WebDAV markers, variable expansion, PSDrive prefixes, and globs be handled when validating one extracted path string?

## Ordered special-form gates BEFORE resolve; deny-guess fallbacks keep hard denies working
**Path/Symbol:** `src/tools/PowerShellTool/pathValidation.ts`:`validatePath` (:1013-1264), `checkDenyRuleForGuessedPath` (:984-1008), `getGlobBaseDirectory` (:1266-1278), provider regex (:1148-1159).
**Signature:** `function validatePath(filePath: string, cwd: string, ctx: ToolPermissionContext, operationType: FileOperationType): { allowed: boolean; resolvedPath: string; decisionReason? }`.
**Data Shape:** Input: raw extracted path (quotes intact possible). Output always carries `resolvedPath` for messages/suggestions.

### Decisive source
```ts
// SECURITY: Backtick (`) is PowerShell's escape character ... defeats Node.js
// path checks like isAbsolute().
if (normalizedPath.includes('`')) {
  const denyHit = checkDenyRuleForGuessedPath(backtickStripped, ...)
  if (denyHit) return { allowed:false, ... rule }   // deny STILL fires
  return { allowed:false, reason:'Backtick escape characters ... cannot be statically validated' }
}
if (normalizedPath.includes('::')) { /* strip up-to-first '::', deny-guess, else ask */ }
// UNC: '//' prefix OR DavWWWRoot OR @SSL@ (SharePoint WebDAV) => blocked
if (normalizedPath.includes('$') || normalizedPath.includes('%')) { /* expansion => ask */ }
const providerPathRegex =
  getPlatform() === 'windows' ? /^[a-z0-9]{2,}:/i : /^[a-z0-9]+:/i
if (providerPathRegex.test(normalizedPath)) { /* env:/HKLM:/PSDrive => ask */ }
```

**Flow:** quote-strip + tilde-expand + backslash→slash normalize → backtick gate (deny-guess on stripped form first!) → `::` module-qualified provider strip (first occurrence only; doubles fall to ask safely) → UNC battery (`//`, DavWWWRoot, @SSL@ — credential-leak vectors) → `$`/`%` expansion rejection → provider-prefix gate with PLATFORM SPLIT (Windows requires 2+ alnum chars so `C:` passes to win32 resolution; POSIX treats ANY drive-like prefix as an unmappable PSDrive — `Z:/secrets` after `New-PSDrive -Name Z -Root /etc` would otherwise resolve inside cwd and bypass Read(/etc/**)) → glob gate (writes: reject outright; reads with traversal: full-resolve; plain read globs: deny-check the base dir then ask because symlinks INSIDE glob expansion are never examined) → finally realpath-resolve into `isPathAllowed` (deny → internal-editable → safety check → working-dir/acceptEdits → sandbox allowlist → allow-rule).
**Invariant:** Every "unvalidatable" branch still runs deny-rule matching over a best-effort stripped guess BEFORE falling to ask — hard denies survive even hostile encodings; only auto-allows are lost. Glob writes never pass; glob reads never trust the expansion.
**Probe:** `grep -nF "DavWWWRoot" src/tools/PowerShellTool/pathValidation.ts | head -1` and `grep -nF "/^[a-z0-9]{2,}:/i" src/tools/PowerShellTool/pathValidation.ts` and `grep -cF "checkDenyRuleForGuessedPath(" src/tools/PowerShellTool/pathValidation.ts` → `4` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "validatePath provider UNC glob backtick deny guess", limit: 10, fields: ["signature", "name", "file"] });
```
*(zod-free file; query-mode resolves `checkPathConstraints` :1528-1567 and `extractPathsFromCommand`; use name_pattern `^validatePath$` for the exact Function row :1013-1264)*

## Verdict
Adopt the ordered ladder with deny-guess-before-ask at every unresolvable form, and the POSIX/Windows PSDrive split. Adapt marker lists (DavWWWRoot/@SSL@) to your environment. Omit SharePoint specifics beyond the markers. Coverage caveat: no upstream tests; graph confirms `checkPathConstraints` :1528-1567 rank#1.
