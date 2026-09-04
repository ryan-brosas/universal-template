<!-- capsule-v2 -->
# Canonical check — dependency-free DSH-template validation gate

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a clonable coding-agent template enforce its own surface, skill membership, foundation depth, profile layer, and commit conventions with a single dependency-free `node scripts/check.mjs` that CI runs identically?

## Dependency-free canonical check
**Path/Symbol:** `scripts/check.mjs` (whole file, 180 lines); helpers `ok`/`fail`/`section` (12–14), the `failures` counter (10), the `FOUND` regex (96).
**Signature:** `node scripts/check.mjs` → exit 0 on all-ok, exit 1 with a failure count on any problem. Imports only `node:child_process` (`spawnSync`), `node:fs` (`existsSync`, `readFileSync`), `node:path` (`join`).
**Data Shape:** `root = process.cwd()`; `failures` counts failures; `skillFiles` accumulates `{ dir, name, isDir }` entries from `.dsh/skills`. Output is `[ok]`/`[fail]` lines grouped under `> <section>` headers; final line `repository check: ok` or `dsh-template check: FAILED (N problems)`.

### Decisive source
```js
// Dependency-free: only node builtins. No package.json at the template root.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
const root = process.cwd();
let failures = 0;
function fail(msg) { console.log("[fail] " + msg); failures++; }

// 1. No Pi/OpenCode remnants
const piSurface = ["opencode.json", "dcp.jsonc", ".pi/fabric.json", ".pi/settings.json", ".pi/skills", ".pi/prompts", ".pi/templates"];
for (const p of piSurface) if (existsSync(join(root, p))) fail("Pi/OpenCode template surface present: " + p);

// 3. Skill frontmatter: name must be kebab-case, description required
const m = body.match(/^---\n([\s\S]*?)\n---/);
const name = fm.match(/^name:\s*(\S+)\s*$/m)?.[1];
if (!name || !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(name)) fail("skill name not kebab-case: " + s.name);
if (!/^description:/m.test(fm)) fail("skill missing description: " + s.name);

// 3b. packs.json membership: every declared member must resolve to pack-<id>/<member>/SKILL.md
for (const pk of packsList) {
  const packDir = join(skillRoot, pk.id);
  for (const m of pk.members) if (!existsSync(join(packDir, m, "SKILL.md")))
    fail("pack member missing SKILL.md: " + pk.id + "/" + m);
}

// 3c. Foundation depth: every *-foundation dir must have references/*.md
const FOUND = /-foundation$/;
if (s.isDir && FOUND.test(s.name)) {
  const refDir = join(s.dir, s.name, "references");
  let hasDoc = false;
  try { hasDoc = existsSync(refDir) && rd(refDir).some(f => f.endsWith(".md")); } catch (_) {}
  if (!hasDoc) fail("foundation has no references doc (expected references/*.md): " + s.name);
}

// 8. Commit-convention gate (unpushed commits only)
const subjectRe = /^(feat|fix|docs|chore|refactor|test)(\([a-z0-9-]+\))?: .+/;
const branchRe = /^(main|master)$|^[a-z0-9]+(-[a-z0-9]+){0,2}$/;
// subjects = git log --format=%s --no-merges origin/main..HEAD
if (failures > 0) { console.error("dsh-template check: FAILED (" + failures + " problems)"); process.exit(1); }
console.log("repository check: ok");
```

**Flow:** (1) reject any Pi/OpenCode template remnant; (2) require `AGENTS.md` at root; (3) scan `.dsh/skills` — every pack member dir must have `SKILL.md` with kebab-case `name` + `description` frontmatter; (3b) parse `.dsh/skills/packs.json` and verify every declared member resolves; (3c) every `*-foundation` dir must contain a `references/*.md`; (3d) `foundations-workflow/SKILL.md` must route through `writing-skills`; (4) require `.dsh/profile/package.json` with nonempty `dsh.profile.bundles` + `cordis.patch.yml`; (5) require `.dsh/home/settings.yaml` + `mcp.yaml`; (6) require `.dsh/workflows/`; (7) `git diff --check`; (8) gate unpushed commit subjects + branch name. Exit 1 on any failure.

**Invariant:** the template stays install-free and dependency-free (only node builtins); every skill carries valid frontmatter; packs.json membership is authoritative and every member resolves; every `*-foundation` has at least one `references/*.md`; CI runs the exact same command as local.

**Probe:** `node scripts/check.mjs` from the template root exits 0 with `repository check: ok` (verified live on this clone, `pi-fovea-foundation`). No direct test file exists — this is the executable gate itself. Coverage caveat: `scripts/` is excluded from the graph index by design, so this is direct-source evidence.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "check.mjs packs.json foundation depth", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dependency-free gate structure (no Pi remnants, frontmatter + packs.json membership, foundation-depth bar, profile/home/workflow presence, `git diff --check`, commit conventions). Adapt the Pi-surface list, the pack layout, and the branch regex to the host. Omit the `vercel-deploy-claimable`/`find-polluter` script checks unless a target needs them.
