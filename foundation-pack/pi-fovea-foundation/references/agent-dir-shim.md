<!-- capsule-v2 -->
# In-process agent-dir shim — why does the extension copy a 10-line path resolution instead of importing the host?

**Source:** pi-fovea MIT `main@5bd4e6f`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** The extension needs pi's agent-dir (~/.pi/agent) — why re-implement it, and which env var must stay honored?

## Copy the leaf resolution, skip the host module graph
**Path/Symbol:** `src/core/agent-dir.ts:resolveAgentDir/configDirName` (:1-19, whole file); consumers `src/ui/settings.ts`, `tests/settings.test.ts`.
**Signature:** `resolveAgentDir(): string` = `PI_CODING_AGENT_DIR` (tilde-expanded) else `~/.pi/agent`.
**Data Shape:** no state, no I/O; pure env+homedir derivation.

### Decisive source
```ts
// pi's agent-dir resolution, in-process so pi-fovea modules never import the
// pi-coding-agent runtime at extension load. pi's loader re-evaluates the host
// module graph for every extension that imports it, costing roughly a second
// of startup.
export const configDirName = ".pi";
export const resolveAgentDir = (): string => {
  const override = process.env.PI_CODING_AGENT_DIR;
  return override ? expandTilde(override) : path.join(homedir(), configDirName, "agent");
};
```

**Flow:** extension load → resolveAgentDir answers from env/homedir with ZERO imports of `@earendil-works/pi-coding-agent` → settings/state paths agree with the host's own dir. (The same laziness discipline appears at the other import site: `import("./ui/settings.js")` is dynamic so the settings UI only loads when opened.)
**Invariant:** the override env var MUST keep winning — tests redirect it to isolate from the developer's real ~/.pi; if the host ever changes its dir scheme this shim must move WITH it (it is a deliberate duplication, not drift).
**Probe:** `tests/settings.test.ts` — sets/restores `PI_CODING_AGENT_DIR` around every case (:62-98) pinning that the override, not homedir, decides.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "resolveAgentDir PI_CODING_AGENT_DIR", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for plugin authors on any host with expensive module graphs: duplicate tiny leaf resolvers rather than pay host-load cost; keep the override contract. Adapt dir names. Omit pi-specific tilde edge cases beyond `~` and `~/`.
