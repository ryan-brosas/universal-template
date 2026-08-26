<!-- capsule-v2 -->
# Git porcelain oracle — how do you answer "what drifted?" in one cheap probe without ever trusting a partially-parsed result?

**Source:** pi-fovea MIT `main@5bd4e6f5c56190fb174245266464607b11f7a337`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** Turn-sync and impact seeding both need the worktree change set every turn — what exact contract must a porcelain probe satisfy so consumers can distinguish "clean", "these files changed", and "I cannot trust this answer"?

## Connected graph-selected seam
**Path/Symbol:** `src/core/git.ts:gitProbe/gitPrefix/gitRelativePath/gitReflogAction` (:50–128); seed helpers `uncommittedFiles/prFiles` (:131–150).
**Signature:** `gitProbe(root): Promise<GitProbe | undefined>` where `GitProbe {head, changes: {code, path}[], relist: boolean}`; `prFiles(root, base): Promise<string[]>` over `diff --name-only base...HEAD`.
**Data Shape:** probe parses `status --porcelain=v1 -z --untracked-files=normal --no-renames -- .` NUL-delimited records into 2-char status codes + prefix-relative paths; `undefined` means "not a git work tree"; `relist: true` means "parse surprise — rescan instead of trusting this set".

### Decisive source
```ts
const fields = out.split("\0").filter((f) => f.length > 0);
const changes: WorktreeChange[] = [];
let relist = false;
for (const field of fields) {
  if (field.length < 4) { relist = true; continue; }
  const code = field.slice(0, 2);
  const path = gitRelativePath(field.slice(3), prefix);
  if (!path) { relist = true; continue; }
  // --no-renames keeps the format to a single path per record; anything
  // else unexpected marks the probe unreliable rather than lossy.
  if (!/^[ MARCUD?!]{2}$/.test(code)) relist = true;
  changes.push({ code, path });
}
```

**Flow:** `rev-parse --show-prefix` (LRU-cached, backslash-normalized) establishes repo-relative mapping → porcelain -z parsed field-by-field → any malformed record, unmappable path, or unknown status code flips `relist` while still returning the parsed changes → consumers (`refreshState`) treat `relist` as "re-list all files"; `gitReflogAction` (`reflog -1 --format=%gs`) classifies HEAD moves: `"checkout:…"` ⇒ quiet re-baseline, anything else ⇒ authored drift; `prFiles(base...)` seeds PR-style impact via three-dot diff.
**Invariant:** The probe never silently drops records it does not understand — uncertainty is explicit (`relist`). Paths are mapped through the show-prefix so probes run from subdirectories yield root-relative names; `--no-renames` guarantees one path per record. All git calls go through `gitOut`: execFile under the shared spawn gate, 15s timeout, failure resolves `undefined` (never throws).
**Probe:** `tests/sync.test.ts` ("re-baselines quietly on a branch switch…" pins the reflog classifier end-to-end; "follows the worktree when a dirty file returns to porcelain-clean" pins probe-driven resurrection); run `pnpm vitest run tests/sync.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "gitProbe gitPrefix gitRelativePath prFiles uncommittedFiles", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-safe-to-relist parsing discipline, prefix-relative path mapping with LRU, the reflog-based checkout-vs-drift classifier, and three-dot-diff PR seeding. Adapt status-code handling if you need rename detection (then parse two-path records explicitly). Omit nothing from the trust model — `relist` is the contract that makes the cheap path safe.
