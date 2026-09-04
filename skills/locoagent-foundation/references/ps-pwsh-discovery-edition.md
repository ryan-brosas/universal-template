<!-- capsule-v2 -->
# PS pwsh discovery and edition split — how do you find PowerShell, avoid snap-launcher hangs, and branch 5.1-vs-7 behavior without spawning?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Where should shell-path discovery live, what platform quirk needs a realpath probe, and how do you infer the edition for prompt guidance?

## Memoized promise + snap-detection ladder + basename edition inference
**Path/Symbol:** `src/utils/shell/powershellDetection.ts`:`findPowerShell` (:24-57), `getCachedPowerShellPath` (:65-70), `getPowerShellEdition` (:87-100); consumers: parser spawn (:1156-1163), provider selection, `prompt.ts` edition section (:51-71).
**Signature:** `function getCachedPowerShellPath(): Promise<string | null>`; `async function getPowerShellEdition(): Promise<'core' | 'desktop' | null>`.
**Data Shape:** Edition is inferred from binary NAME ONLY (`pwsh*` ⇒ core ⇒ 7+ semantics incl. `&&`/`||`/`?:`/`??`; `powershell*` ⇒ desktop 5.1; PS6 EOL ignored) — no version spawn.

### Decisive source
```ts
// On Linux, if PATH resolves to a snap launcher (/snap/…) — directly or
// via a symlink chain like /usr/bin/pwsh → /snap/bin/pwsh — probe known
// apt/rpm install locations instead: the snap launcher can hang in
// subprocesses while snapd initializes confinement, but the underlying
// binary at /opt/microsoft/powershell/7/pwsh is reliable.
if (getPlatform() === 'linux') {
  const resolved = await realpath(pwshPath).catch(() => pwshPath)
  if (pwshPath.startsWith('/snap/') || resolved.startsWith('/snap/')) {
```

**Flow:** which('pwsh') → Linux-only snap check on BOTH the PATH entry AND its realpath target (`/usr/bin/pwsh` symlink would bypass a naive startsWith) → prefer `/opt/microsoft/powershell/7/pwsh` then `/usr/bin/pwsh`, re-validating the fallback isn't ALSO snap-resolved → else return PATH hit → fall back to which('powershell') → null. Result memoized as a promise (single discovery per process; `resetPowerShellCache` for tests). Parser treats null as typed failure `NoPowerShell`.
**Invariant:** Discovery must be promise-memoized because it sits on EVERY parse call; the edition inference must never spawn (it runs during prompt build where a hung shell would stall startup), so name-basename is the contract. Unknown edition ⇒ conservative 5.1 guidance in prompts (no `&&` advice).
**Probe:** `grep -nF "startsWith('/snap/')" src/utils/shell/powershellDetection.ts | wc -l` → `4` and `grep -nF "return base === 'pwsh' ? 'core' : 'desktop'" src/utils/shell/powershellDetection.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "findPowerShell getCachedPowerShellPath snap", limit: 10, fields: ["signature", "name", "file"] });
```
*(resolves parser/provider consumers of the cached path)*

## Verdict
Adopt memoized-promise discovery, dual-entry snap detection, and name-based edition inference. Adapt install-location candidates over time. Omit distro lore beyond the two paths. Coverage caveat: probes deterministic; no upstream tests.
