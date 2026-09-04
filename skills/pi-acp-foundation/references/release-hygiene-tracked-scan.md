<!-- capsule-v2 -->
# Release-hygiene tracked scan — how do you keep a reusable template repo free of machine paths, secrets, tracked runtime state, and stale documented counts?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** A repo that ships as a reusable template accumulates four rot classes invisible to tests: machine-specific absolute paths, credential-shaped strings, tracked runtime state, and README counts that no longer match the tree. How do you scan for all four — over exactly what ships, not what sits in the working tree?

## Four scan classes over `git ls-files`, with a documented CI-path exception and count reconciliation
**Path/Symbol:** `scripts/validate-release-hygiene.mjs` (whole, 79L) — tracked-file universe :13-18, HOME_RE + runner exception :22-29, SECRET_RE :32-38, RUNTIME_RE :41-43, count reconciliation :46-70, final ok line :77-79.
**Signature:** `node scripts/validate-release-hygiene.mjs [root]` (default `process.cwd()`; uses `spawnSync('git', ['ls-files'])` — must run inside the repository).
**Data Shape:** three compiled regexes over tracked-file text: `HOME_RE = /\/(home|Users)\/(?!runner(?:\/|$))[^\/\s]+(?:\/|$)/`; `SECRET_RE` alternation of `sk-…20+`, `ghp_…30+`, `github_pat_…20+`, `AKIA…16`, and PEM private-key blocks; `RUNTIME_RE = /^(?:\.pi\/(?:MEMORY\.md|implementation-notes\.md|fabric\/)|\.veda(?:\/|$))/` tested against tracked PATHS.

### Decisive source
```js
// :22-29 machine paths, with the documented GHA CI path excepted by lookahead
const HOME_RE = /\/(home|Users)\/(?!runner(?:\/|$))[^\/\s]+(?:\/|$)/
for (const f of files) {
  const full = join(root, f)
  if (!existsSync(full)) continue // tracked-but-deleted working-tree files (unstaged cleanup)
  const text = readFileSync(full, 'utf8')
  const m = text.match(HOME_RE)
  if (m) fail(`machine-specific absolute path ${m[0].trim()} in ${f}`)
}
// :46-49 skip gate — but the body below needs .pi/prompts AND .pi/templates
if (!existsSync(join(root, '.pi'))) {
  console.log('[skip] README count checks; .pi is not in this checkout')
  process.exit(0)
}
const prompts = readdirSync(join(root, '.pi', 'prompts')).filter(n => n.endsWith('.md')).length
```

## Flow
1. Universe = `git ls-files` (:13-18) — the RELEASE SURFACE (what ships), not the working tree; untracked local files are invisible to this gate by design.
2. Scan 1 — machine paths: any `/home/<user>` or `/Users/<user>` absolute path fails, EXCEPT `/home/runner` (the documented GitHub Actions CI path in CLI references) via negative lookahead.
3. Scan 2 — credential shapes: OpenAI `sk-`, GitHub `ghp_`/`github_pat_`, AWS `AKIA`, PEM private-key headers fail on sight.
4. Scan 3 — tracked runtime state: `.pi/MEMORY.md`, `.pi/implementation-notes.md`, `.pi/fabric/`, `.veda` must stay untracked — the gate fails if local agent state ever enters the release surface.
5. Scan 4 — documented counts: README's "N prompt commands", "N skill files", "N format templates", "N leaves in N packs" must equal the live tree (leaves = Σ pack.members + visibleCore; skillFiles = leaves + packs), with BOTH sides printed in the failure so you know which end drifted.
6. Exit: accumulated errors → `[fail]` list + exit 1; else a one-line `[ok] tracked=N prompts=N skills=N …` summary.

## Invariant
- Scan the tracked universe only: hygiene applies to what ships; a dirty working tree is not a release defect.
- Documented exceptions must be encoded as regex structure (the `/home/runner` lookahead), not as comment prose — the regex is the contract.
- Count reconciliation prints both sides (README vs tree) so the fix direction is unambiguous.
- **Deepest-path gate defect (live):** the skip gate checks only `.pi` (:46) but the count section reads `.pi/prompts` (:50), `.pi/templates` (:51), and `.pi/skills/packs.json` (:52) — on a checkout with a partial gitignored `.pi/` it CRASHES with unhandled `ENOENT` at `readdirSync(.pi/prompts)` :50, exit 1. Gate granularity must match the deepest touched path. (This pass re-confirms :50; pass-7's work-management ":50" attribution was this script's line.)

## Probe
No direct unit test exists for this script at this pin (recorded caveat). Executed live probe:
```
node scripts/validate-release-hygiene.mjs
# → Error: ENOENT … scandir '…/.pi/prompts' at validate-release-hygiene.mjs:50 → exit 1
```
(The scans over tracked files themselves ran clean — the crash is the count section's skip-gate granularity.)

## Retrieve
`search_graph(project="pi-acp", q="validate-release-hygiene HOME_RE SECRET_RE tracked runtime state README counts", mode="ids")` — revalidate at the current pin (graph unavailable passes 5–8; direct read is the authority).

## Adopt/Adapt/Omit Verdict
**Adopt.** Adopt: scanning `git ls-files` as the release surface; the four rot classes (machine paths, credential shapes, tracked runtime state, documented counts) as one gate; regex-structured documented exceptions; two-sided count mismatch messages; tracked-but-deleted tolerance. Adapt: gate on the deepest path your count section reads (the :50 crash is the counterexample); the secret-shape alternation should track your org's token formats (the auto-commit watcher's detectSecrets is the working-tree twin of this release-surface scan). Omit: the repo-specific README count labels.
