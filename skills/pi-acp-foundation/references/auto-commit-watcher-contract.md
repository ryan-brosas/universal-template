<!-- capsule-v2 -->
# Auto-commit watcher contract — how do you run an interval auto-commit watcher that never pushes and never commits secrets?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A dev-tree watcher snapshots all working changes every 60s so agent sessions never lose work — but it must be safe to leave running unattended: no remote push, no secret commit, no crash on a bad sweep. What is the minimal gate ladder that makes that safe, and what does the rest of the codebase have to do to stay correct while the tree keeps getting swept?

## Secret-gated 60s sweep with log-don't-throw survival
**Path/Symbol:** `scripts/auto-commit.mjs` (whole, 93L) — constants + patterns :9-16, `changedPaths` :26-31, `detectSecrets` :33-46, `snapshot` :48-75, signal handlers + loop :77-93. Consumer in src/: `src/acp/ide-inspection.ts` :79 (`extraFiles` doc) and :121-128 (`mergeInspectFiles` doc) — the post-turn inspection gate merges turn-touched tool-call paths with git status precisely because this watcher can clear git status between turn end and the gate (see `references/post-turn-inspection-gate.md`).
**Signature:** `node scripts/auto-commit.mjs` (no args; repo root derived from `import.meta.url` parent; `intervalMs = 60_000`, `maxScannedBytes = 10 * 1024 * 1024`).
**Data Shape:** changed paths from `git ls-files -m -o --exclude-standard -z` (NUL-split, deduped via Set); secret findings as `"<path>: <pattern-name>"` strings; commit message = `chore(auto): snapshot changes at <ISO timestamp>` + fixed body ("No remote push was performed.") + `git diff --cached --name-status --no-renames` details.

### Decisive source
```js
function snapshot() {
  const paths = changedPaths()
  if (paths.length === 0) return
  const findings = detectSecrets(paths)
  if (findings.length > 0) {
    console.error(`[auto-commit] blocked: possible secrets found\n${findings.join('\n')}`)
    return                       // blocked sweep: log + skip, NEVER commit
  }
  const add = git(['add', '-A'])
  // ... commit message embeds name-status details + "No remote push was performed."
}
// loop:
while (!stopped) {
  await new Promise(resolve => setTimeout(resolve, intervalMs))
  if (stopped) break
  try { snapshot() } catch (error) {
    console.error(`[auto-commit] ${error instanceof Error ? error.message : String(error)}`)
  }   // a bad sweep is logged, never fatal — the watcher survives
}
```
```js
// scan bounds inside detectSecrets:
if (!stat.isFile() || stat.size > maxScannedBytes) continue
const text = readFileSync(absolutePath, 'utf8')
if (text.includes('\0')) continue        // binary ⇒ skip, don't decode
```

**Flow:** every 60s: list changed tracked+untracked non-ignored paths → empty ⇒ no-op sweep → else scan each file for four secret patterns (private-key block, `gh[pousr]_` GitHub token, `AKIA|ASIA` AWS key, `xox[baprs]-` Slack token) under the bounds (regular files only, ≤10MB, NUL-byte ⇒ binary skip) → any finding ⇒ print `blocked:` + findings and SKIP the whole sweep → else `git add -A`, read staged `--name-status --no-renames`, empty ⇒ return, else commit with the timestamped message. SIGINT/SIGTERM set a `stopped` flag checked after each sleep (clean stop at the next boundary). Any thrown error in a sweep is caught and logged — the loop continues.
**Invariant:** the watcher NEVER pushes (no remote command exists anywhere in the script) and NEVER commits a sweep whose changed files trip a secret pattern — blocking skips the entire sweep rather than committing the clean subset, so a secret file can't ride along with innocent ones in a partial commit. Sweeps are idempotent no-ops on a clean tree, and one bad sweep can only lose that sweep's snapshot, never the process. Downstream consumers must not assume git status reflects the current turn's edits: the inspection gate therefore takes `extraFiles` (turn-touched tool-call paths) merged over git status.
**Probe:** LIVE this pass: ran the real script against the pinned checkout for ~11 minutes (multiple sweeps) on a clean tree → zero commits, HEAD unchanged, `git status --porcelain` empty (no-op-sweep contract confirmed byte-for-byte). Secret-block path is source-read only this pass (creating a secret-named file in the read-only lane checkout is forbidden); no direct unit test exists for this script.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "auto-commit detectSecrets mergeInspectFiles extraFiles", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full-sweep block-on-secret (never partial-commit), the bounded scan (size cap + NUL-binary skip so the gate can't hang or misdecode), the log-don't-throw sweep loop, the flag-checked stop boundary, and the explicit "No remote push" contract in the commit body; adopt the consumer-side discipline too — anything that reads "what changed this turn" from git status must merge in its own turn-touched path list because a sweep may have committed (and cleared) the tree. Adapt the pattern table to your credential vocabulary and the interval to your session cadence. Omit running it in CI or on shared checkouts — it commits by design; keep it a local dev-tree convenience.
