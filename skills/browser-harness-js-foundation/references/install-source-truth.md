<!-- capsule-v2 -->
# Source-of-truth install model — why do installed copies drift, and what makes staleness detectable and repairable?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the repo→installed→PATH symlink chain, and which rules prevent agents from editing the wrong copy?

## Edit only ./skills; installs are copies; PATH via per-skill setup symlink; version bump + --restart
**Path/Symbol:** `AGENTS.md` (whole file — the contract: install table :21-31, version rule :37-62, anatomy :64-141); `connection.md` stale-daemon section (:135-159); launcher `sdk/browser-harness-js` (`--version` fresh read vs `/health` boot cache).
**Signature:** process contract: develop in `./skills/<name>/` → each skill's `scripts/setup` symlinks `~/.local/bin/<name>` → repo script (and `browser-harness-js` → `../cdp/sdk/browser-harness-js`) → users install on their own schedule via `npx skills add`.
**Data Shape:** three locations with one write-allowed: repo (source of truth) / `~/.agents/skills/<name>` (installed copy — NEVER edit) / `~/.pi/agent/skills/<name>` (symlink to it — NEVER edit).

### Decisive source
```md
| ./skills/<name>/ (this repo)      | source of truth              | YES — always |
| ~/.agents/skills/<name>/          | installed copy               | NO |
| ~/.pi/agent/skills/<name>         | symlink → ~/.agents copy     | NO |
```
```md
Bump `"version"` on every change to the `cdp` skill … Without a bump, an
installed copy has no way to know it's behind.
```
Staleness tells: `ReferenceError: <global> is not defined` for a documented global (docs newer than daemon), or `--version` (disk) > `/health.version` (boot memory) ⇒ fix = `browser-harness-js --restart` (drops session state; reconnect + re-use target after).

**Flow:** edit repo files → bump `skills/cdp/sdk/package.json` version (patch for fixes/docs, minor for capabilities) → `bash skills/<name>/scripts/setup` to refresh the PATH symlink for local testing → smoke test (`scripts/test`, exit 77 = browser unreachable) → daemon keeps running OLD code until `--restart`.
**Invariant:** (1) Writes into installed copies are throwaway by definition — changes there never flow back. (2) The version field exists SOLELY as the staleness oracle; skipping the bump silently breaks update detection. (3) Restarting drops in-memory session state but not `globalThis.*` persistence guarantees across restarts — re-connect/re-attach is part of every restart procedure. (4) New globals added to repl.ts are invisible until restart even though docs describe them.
**Probe:** no test (process contract). Deterministic probes: launcher's dual reads — `grep -n "sdk_version\|--version" skills/cdp/sdk/browser-harness-js` vs boot-cached `VERSION` in repl.ts (:24-28).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "listPageTargets", limit: 3, fields: ["signature", "name", "file"] });
// the global most likely to trigger the ReferenceError tell when a daemon is stale
```

## Verdict
Adopt the single-source + copied-installs + version-oracle model for any skill/plugin repo with installed copies; adapt the installer mechanics; omit the bump discipline only if your installs hot-reload (theirs deliberately do not).
