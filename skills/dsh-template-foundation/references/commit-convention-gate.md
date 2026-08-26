<!-- capsule-v2 -->
# Commit-convention gate — unpushed-only conventional-commit + branch-name enforcement

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a dependency-free script enforce commit-subject and branch-name conventions WITHOUT failing on the repository's own pre-existing history?

## Unpushed-window convention gate with CI-aware branch detection
**Path/Symbol:** `scripts/check.mjs` section 8 "Commit-convention gate (unpushed commits only)" (:156–174); regexes `subjectRe` (:158), `branchRe` (:159).
**Signature:** `subjectRe = /^(feat|fix|docs|chore|refactor|test)(\([a-z0-9-]+\))?: .+/`; `branchRe = /^(main|master)$|^[a-z0-9]+(-[a-z0-9]+){0,2}$/`.
**Data Shape:** window = `git log --format=%s --no-merges origin/main..HEAD`; branch = `$GITHUB_HEAD_REF` if set (CI PR context) else `git branch --show-current`. Gate is SKIPPED (prints ok, never fails) when: no `origin/main` ref resolves, or not inside a git work tree (section 7's guard), or zero unpushed commits.

### Decisive source
```js
// ── 8. Commit-convention gate (unpushed commits only)
const subjectRe = /^(feat|fix|docs|chore|refactor|test)(\([a-z0-9-]+\))?: .+/;
const branchRe = /^(main|master)$|^[a-z0-9]+(-[a-z0-9]+){0,2}$/;
if (spawnSync("git", ["rev-parse", "--verify", "origin/main"], { cwd: root, stdio: "ignore" }).status !== 0) {
  ok("no origin/main ref; gate skipped");
} else {
  const subjects = spawnSync("git", ["log", "--format=%s", "--no-merges", "origin/main..HEAD"], { cwd: root, encoding: "utf8" })
    .stdout.trim().split("\n").filter(Boolean);
  if (subjects.length === 0) ok("no unpushed commits");
  else for (const s of subjects) {
    if (subjectRe.test(s)) ok(s.slice(0, 72));
    else fail("subject not conventional: " + s.slice(0, 72));
  }
  const branch = process.env.GITHUB_HEAD_REF ||
    spawnSync("git", ["branch", "--show-current"], { cwd: root, encoding: "utf8" }).stdout.trim();
  if (branch && !branchRe.test(branch)) fail("branch name violates convention: " + branch);
  else if (branch) ok("branch name: " + branch);
}
```

**Flow:** (1) skip silently when there is no `origin/main` (fresh clones / non-git checkouts are never failed by history they did not write); (2) list ONLY unpushed merge-excluded subjects — the repo may violate its own convention historically without blocking new work; (3) each violating subject fails with its first 72 chars; (4) branch name checked against ≤3 lowercase hyphen-words, no slashes, no type prefixes (`main`/`master` exempt); on CI pull-requests the env var overrides local branch detection because `--show-current` reports a detached/empty HEAD in that context.
**Invariant:** the gate judges only work this checkout ADDED (`origin/main..HEAD`) — legacy history is out of jurisdiction; empty window ⇒ pass; missing upstream ref ⇒ pass. The subject regex requires `type:` or `type(scope): ` plus a non-empty summary.
**Probe:** live run at HEAD `ffb36822` → `[ok] no unpushed commits` + `[ok] branch name: pi-fovea-foundation` inside exit-0 output. No direct test file exists (coverage caveat: the executable gate IS the probe).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "check failures section skillFiles packs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the unpushed-window scoping (`origin/main..HEAD`, `--no-merges`) so convention gates never fail on inherited history, and the env-var-first branch detection for PR contexts. Adapt allowed types, scope charset, and branch-word budget to the host. Omit the branch check entirely if your target uses trunk-based naming you cannot express in one regex.
