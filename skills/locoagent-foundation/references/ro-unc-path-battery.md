<!-- capsule-v2 -->
# UNC path battery — one shared detector that keeps Windows SMB credential leakage out of every validation tier

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you detect every UNC spelling that triggers NTLM/Kerberos or WebDAV credential leakage before any validator approves the command?

## Path/Symbol
**Path/Symbol:** `src/utils/shell/readOnlyCommandValidation.ts` — `containsVulnerableUncPath` (:1562-1638), 8-pattern battery; consumers: `isCommandReadOnly` (:1690-1692, post-split) AND `checkReadOnlyConstraints` (:1901-1909, pre-split with behavior 'ask'), PowerShellTool's own hasSyncSecurityConcerns mirror.
**Signature:** `containsVulnerableUncPath(pathOrCommand: string): boolean` — Windows-gated (`getPlatform() !== 'windows'` ⇒ false).
**Data Shape:** regex battery over the raw string; no tokenization.

### Decisive source
```ts
// 3. Check for mixed-separator UNC paths (forward slash + backslashes)
// On Windows/Cygwin, /\ is equivalent to // since both are path separators.
// In bash, /\server becomes /server after escape processing... Requires 2+
// backslashes after / because a single backslash just escapes the next char
const mixedSlashUncPattern = /\/\\{2,}[^\s\\/]/
```
```ts
// 5. Check for WebDAV SSL/port patterns
// Examples: \\server@SSL@8443\path, \\server@8443@SSL\path
if (/@SSL@\d+/i.test(pathOrCommand) || /@\d+@SSL/i.test(pathOrCommand)) {
  return true
}
```

**Flow:** eight ordered checks: (1) backslash UNC `\\host` incl. `@port`, hostname class `[^\s\\/]+` to catch Unicode homoglyphs, trailing `\`/`/`/EOL/space; (2) forward-slash `//host` with negative lookbehind excluding `scheme:` URLs; (3)/(4) mixed-separator forms (escape-processing aware); (5) WebDAV @SSL@port markers either order; (6) DavWWWRoot redirector marker; (7)/(8) explicit IPv4 and bracketed-IPv6 defense-in-depth. Runs at TWO layers in the bash consumer: pre-split on the original command (ask) and per-subcommand inside isCommandReadOnly.

**Invariant:** (1) Detection, not normalization — never "fix" the path into a safe form; reject it. (2) The credential-leak primitive lives in file CONTENTS too (cat a file containing a UNC path → xargs cat → SMB attempt), which is exactly why Windows drops xargs from the allowlist entirely — string-level detection cannot see piped content. (3) Both separator conventions must be checked because bash escape processing converts between them at runtime. (4) The lookbehind exception (`(?<!:)`) exists so https:// URLs don't false-positive while //server still matches.

**Probe:** no upstream tests reachable — coverage caveat. Pins from repo root: `grep -nF "DavWWWRoot/i.test" src/utils/shell/readOnlyCommandValidation.ts` → :1615; `grep -nF "mixed-separator UNC paths (forward slash + backslashes)" src/utils/shell/readOnlyCommandValidation.ts` → :1589.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "containsVulnerableUncPath UNC WebDAV", limit: 6 });
// → ghIsDangerousCallback neighborhood; containsVulnerableUncPath :1562-1638 (cite range directly if ranked below transport twins)
```

## Verdict
Adopt the 8-pattern battery verbatim for any Windows-capable host; on non-Windows hosts keep the function but let it short-circuit (as upstream does). Adapt nothing structural. Omit IPv4/IPv6 sub-checks only if you accept losing defense-in-depth.
