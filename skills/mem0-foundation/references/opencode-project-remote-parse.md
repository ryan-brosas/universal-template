<!-- capsule-v2 -->
# OpenCode project-remote parse — how do you derive a stable project id from a git remote in ONE regex, and what fallback ladder keeps it working outside repos?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when memories must be scoped to "this repo" across clones, worktrees, and sub-directories, what single parser handles every git remote URL form, and what does the identity ladder do when no remote exists?

## project.ts — one regex for https, scp-ssh, host aliases, .git, trailing slash
**Path/Symbol:** `integrations/mem0-plugin/.opencode-plugin/project.ts` — `parseProjectFromRemote` (16–20); ladder consumer `getProjectId` in `opencode-mem0.ts` (39–58).
**Signature:** `parseProjectFromRemote(remote: string): string | null`.
**Data Shape:** pure string→string|null; output is the flat slug `owner-repo` used as mem0's `app_id`. No I/O, no state — the purity is deliberate ("Keeping the parser pure makes the tricky remote formats testable").

### Decisive source
```ts
export function parseProjectFromRemote(remote: string): string | null {
  const m = remote.trim().match(/[:/]([^/:]+)\/([^/:]+?)(?:\.git)?\/?$/);
  if (!m) return null;
  return `${m[1]}-${m[2]}`;
}
```
The anchor `[:/]` before the owner group is what makes scp-style `git@github.com:owner/repo.git` and custom host aliases (`git@github.com-work:owner/repo.git`) work with the SAME pattern as `https://host/owner/repo(.git)?/`.

**Flow:** `getProjectId($)` ladder, each rung fail-open into the next: (1) `MEM0_APP_ID` env override → (2) `git remote get-url origin` piped through the parser → (3) `basename(git rev-parse --show-toplevel)` — the repo ROOT dir name, not cwd, because cwd may be a sub-directory or the home dir when the host launched outside a repo → (4) `basename(process.cwd())`. Every rung is wrapped so a missing git/binary degrades silently.
**Invariant:** the parser must return null (never a partial/garbage slug) when no owner/repo pair exists — garbage app_ids would silently fork the memory namespace; the root-dir-name rung must use `--show-toplevel`, not cwd, or sub-directory launches fragment identity. Contrast the Python hook suite's strategy (plugin-project-remote-hash-selfheal.md): that side hashes the remote (`sha256(origin)[:16]`) and persists a dual-key map with self-heal for renames/moves; this TS side deliberately drops persistence — identity is recomputed each launch from the live remote, trading rename-tolerance for zero state.
**Probe:** `.opencode-plugin/project.test.ts` (6 tests, bun green) — pins the host-alias ssh form, standard scp ssh, https with and without `.git`, trailing-slash tolerance, and null on `"not-a-remote"` / `""`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "parseProjectFromRemote", limit: 10, fields: ["signature", "name", "file"] });
```
(MCP not connected this session — direct whole-file reads of project.ts + project.test.ts + getProjectId executed instead; record in verification.md pass 10.)

## Verdict
Adopt the pure-parser + fail-open-ladder split and the toplevel-not-cwd rule. Adapt the slug format to your store's id constraints (the hyphen join can collide on `a-b/c` vs `a/b-c` — the Python hash strategy exists precisely to avoid that class of collision; pick per your collision tolerance). Omit the env override if your host has a config channel. Coverage: fully indexed plane, whole 20L file + 29L test read; ladder lines read directly from opencode-mem0.ts.
