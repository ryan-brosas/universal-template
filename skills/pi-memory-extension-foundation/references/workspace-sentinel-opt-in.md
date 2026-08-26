<!-- capsule-v2 -->
# Workspace opt-in gate — when does a project's memory layer activate?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must know what makes workspace memory "exist" — directory presence or a sentinel file — and which root the loader anchors to.

## Git-root anchoring + sentinel detection (`findGitRoot` + `session_start`/refresh handlers)
**Path/Symbol:** `pi-memory.ts:findGitRoot` (:62–73); activation logic at :250–258 (identical block in `/memory:refresh` :328–336).
**Signature:** `async function findGitRoot(from: string): Promise<string | null>`.
**Data Shape:** Returns trimmed `git rev-parse --show-toplevel` output or `null` on any failure (non-repo, git absent, 3000ms timeout).

### Decisive source
```ts
async function findGitRoot(from: string): Promise<string | null> {
  try {
    const { execSync } = await import("node:child_process");
    return execSync("git rev-parse --show-toplevel", { cwd: from, encoding: "utf-8", timeout: 3000 }).trim();
  } catch { return null; }
}
...
const gitRoot = await findGitRoot(cwd);
if (gitRoot) {
  const wsDir = path.join(gitRoot, config.workspaceDir);
  const wsIndex = await tryReadFile(path.join(wsDir, "index.md"));
  if (wsIndex) {                    // <-- SENTINEL, not directory existence
    workspaceRoot = wsDir;
    workspaceFiles = await loadLayer(wsDir, "workspace", config);
  }
}
```

**Flow:** resolve git root from `ctx.cwd` → anchor `workspaceDir` to the GIT ROOT (not ctx.cwd — works from nested subdirectories) → treat `<root>/.pi/memory/index.md` as the sole opt-in signal → only then scan the layer.
**Invariant:** Workspace memory is OPT-IN via an `index.md` sentinel; a `.pi/memory/` directory without that file is invisible. Anchoring to the git root means sessions launched from subdirs still bind the project's memory. All git failures collapse to `null` (never throws), and non-git projects simply have no workspace layer. The SAME three-step sequence (global load → detect → merge) is duplicated verbatim in `session_start` (:240–274) and `/memory:refresh` (:318–349) — a porter must keep both in sync or refresh drifts from startup.
**Probe:** NO upstream tests exist. Executed probe (`/tmp/pime-probe/probe2.mts`, Node v26.7.0, GREEN): `null` outside any repo (probe dir is untracked tmp), real repo root resolved for a known tracked path with 3s timeout honored. Sentinel branch confirmed by direct source read (both call sites identical).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory-extension", query: "findGitRoot", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sentinel-file opt-in + VCS-root anchoring for per-project memory layers (directory presence alone must NOT activate). Adapt root-finder to host VCS or config. Omit nothing. Coverage caveat: pinned by executed probe + source read; no upstream suite.
