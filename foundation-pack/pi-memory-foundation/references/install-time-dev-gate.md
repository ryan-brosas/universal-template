<!-- capsule-v2 -->
# Install-time dev gate — how can a postinstall script configure the DEVELOPER's git hooks without ever touching a consumer's repo or VCS config?

**Source:** pi-memory (MIT) `main@39e6b998a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory` (full mode 380n/941e @2026-08-22T23:46:09Z; symbols `scripts.postinstall.isDevCheckout` :12–15, `configureGitHooks` :20–33). **Question:** How do you ship lifecycle setup in an npm package that behaves differently for dev checkouts vs dependency installs, with zero risk to end users?

## Install-time dev gate
**Path/Symbol:** `scripts/postinstall.cjs` — `isDevCheckout` (:12–17), `configureGitHooks` (:20–33), root gate (:35–37).
**Signature:** `isDevCheckout(): boolean = !packageRoot.split(path.sep).includes("node_modules") && fs.existsSync(<root>/.githooks)`; `configureGitHooks()` = `git rev-parse --is-inside-work-tree` probe → `spawnSync("git", ["config", "core.hooksPath", ".githooks"], { cwd: packageRoot })`.
**Data Shape:** no writes outside this repo's local `.git/config`; every spawn passes `stdio: "ignore"` and `shell: process.platform === "win32"`.

### Decisive source
```js
// Two independent gates: path-shape AND repo marker. Either alone misfires.
function isDevCheckout() {
  if (packageRoot.split(path.sep).includes("node_modules")) return false;
  return fs.existsSync(path.join(packageRoot, ".githooks"));
}
function configureGitHooks() {
  const insideRepo = spawnSync("git", ["rev-parse", "--is-inside-work-tree"], {
    cwd: packageRoot, stdio: "ignore", shell: process.platform === "win32",
  });
  if (insideRepo.status !== 0) return;      // not a work tree → silently do nothing
  spawnSync("git", ["config", "core.hooksPath", ".githooks"], { ... });
}
```

**Flow:** npm runs postinstall → dev checkout (no `node_modules` segment + `.githooks` tracked) gets `core.hooksPath=.githooks` scoped to THIS repo only → consumer install (`node_modules` path shape) exits without touching anything.
**Invariant:** never mutate VCS state from a package lifecycle script unless two independent signals confirm you're in your own source checkout; scope every write to the package root's own config; fail silent-and-safe on any probe miss. The deliberate qmd non-nag (optional tool; pi surfaces instructions contextually via `ctx.ui.notify`) keeps installs quiet — don't add banner spam back.
**Probe:** EXECUTED this pass at HEAD, both polarities: dev checkout `node scripts/postinstall.cjs` → exit 0 and `git config core.hooksPath` = `.githooks`; consumer twin under `/tmp/pimem-consumer/node_modules/postinstall.cjs` (inside a fresh `git init`) → exit 0 and `core.hooksPath` STILL UNSET (consumer untouched). Repo state restored (`core.hooksPath` unset) after the probe.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "postinstall isDevCheckout configureGitHooks core.hooksPath", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-signal dev-checkout gate + repo-scoped `core.hooksPath` pattern for any npm/pypi lifecycle script that wants developer conveniences. Adapt marker names (`.githooks`, path segments) to your layout. Omit consumer-side behavior entirely — that is the point.
---
