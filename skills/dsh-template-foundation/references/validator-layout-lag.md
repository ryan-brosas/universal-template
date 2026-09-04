<!-- capsule-v2 -->
# Validator layout lag — the gate's path constants must migrate with the template layout

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** What happens when a template migrates its directory layout (root `profile/`, `home/`, `workflows/` → `.dsh/*`) without updating the validator that checks those very paths — and what does the correct migration invariant look like?

## Self-check drift: sections 4–6 vs the `.dsh/` namespace
**Path/Symbol:** `scripts/check.mjs:119-143` at HEAD — §4 "profile layer" (`profPkg = join(root, "profile", "package.json")` :121, `cordis.patch.yml` check :128), §5 "home templates" (`for (const p of ["home/settings.yaml", "home/mcp.yaml"])` :135), §6 "workflows" (`join(root, "workflows")` :142). The committed tree ships these surfaces ONLY under `.dsh/profile/…`, `.dsh/home/…`, `.dsh/workflows/`.
**Signature:** `node scripts/check.mjs` → exit 1, `dsh-template check: FAILED (5 problems)`: `profile/package.json missing`, `profile/cordis.patch.yml missing`, `home/settings.yaml missing`, `home/mcp.yaml missing`, `workflows/ missing`.
**Data Shape:** the failure is structural, not content: every checked artifact EXISTS in the tree — one level deeper than the gate's path constants expect. Sections 1–3 pass (Pi-remnant scan, AGENTS.md, `.dsh/skills` + packs.json + foundation depth); only the three layout-migrated planes fail.

### Decisive source
```js
// ── 4. Profile layer ──────────────────────────────────────────────
const profPkg = join(root, "profile", "package.json");   // ← root-relative
if (!existsSync(profPkg)) fail("profile/package.json missing"); // FAILS at HEAD
// …
// ── 5. Home templates ────────────────────────────────────────────
for (const p of ["home/settings.yaml", "home/mcp.yaml"]) { // ← root-relative
  if (!existsSync(join(root, p))) fail(p + " missing");    // FAILS ×2 at HEAD
}
// ── 6. Workflows dir ─────────────────────────────────────────────
if (existsSync(join(root, "workflows"))) ok("workflows/ present");
else fail("workflows/ missing");                            // FAILS at HEAD
```
The uncommitted working-tree fix (verified via `git diff scripts/check.mjs`) rewrites exactly these constants to `join(root, ".dsh", "profile", "package.json")`, `[".dsh/home/settings.yaml", ".dsh/home/mcp.yaml"]`, and `join(root, ".dsh", "workflows")` — confirming the root-relative paths are stale constants, not intentional checks.

**Flow:** (1) template author migrates surfaces into the `.dsh/` namespace; (2) `check.mjs` §4–6 still probe the OLD root-relative locations; (3) on a pristine clone of the pin, five `[fail]` lines fire and the canonical check exits 1 even though every required file ships in the repo; (4) CI (`check.yml`) runs this same script, so the strict-gate run would be red on the migrated layout until the constants move with it.

**Invariant:** a template validator's path constants are part of the template contract — when the layout moves, the validator MUST move in the SAME change, or a pristine checkout fails its own gate (fresh-clone ≠ worktree where uncommitted fixes live). Porting lesson: after any layout migration, re-run the canonical check from a CLEAN clone before trusting green.

**Probe:** no direct test file exists. EXECUTED at HEAD: `git archive HEAD | tar -x -C /tmp/dsh-head-probe && cd /tmp/dsh-head-probe && node scripts/check.mjs` → rc=1, `FAILED (5 problems)` with the five misses listed above; identical command in the live worktree → exit 0 (the uncommitted constant fixes close the gap). This clean-clone-vs-worktree asymmetry IS the pinned behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "profile package.json home settings workflows", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the invariant: validator path constants migrate atomically with template layout, verified from a clean clone (archive-extract probe). Adapt the specific section list to your own gate. Omit nothing — this capsule is a process guard, not a feature to port.
