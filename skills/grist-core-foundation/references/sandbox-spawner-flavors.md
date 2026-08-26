<!-- capsule-v2 -->
# Sandbox spawner flavors — how do you swap isolation backends without touching call sites?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you let one deployment run the same data engine unsandboxed, in docker, under gvisor, under macOS sandbox-exec, or as an in-process WASM runtime — selected by env/config at spawn time?

## One SpawnFn table + FlagBag wrapper args; capability probe decides fallback chain
**Path/Symbol:** `app/server/lib/NSandbox.ts`: `spawners` table (523–538), `NSandboxCreator` (561–623), `createSandbox` spec parser (1357–1369), `createConcreteSandbox` (1331–1342), `sandboxed` fallback (784–791), `gvisor` (909–1007), `docker` (1015–1058), `macSandboxExec` profile builder (1068–1161), `unsandboxed` (800–833), `getInsertedEnv`/`getWrappingEnv` (1166–1210), `getAbsolutePaths` (1220–1236), `FlagBag` (1243–1273), `findPython` (1282–1312), `adjustedSpawn` choom wrapper (1384–1391), availability probes `getAvailableSandboxes`/`testSandboxFlavor` (635–760).
**Signature:** `type SpawnFn = (options: ISandboxOptions) => SandboxProcess`; `new NSandboxCreator({ defaultFlavor, command?, commandArgs?, commandAppendArgs?, preferredPythonVersion? }).create(ISandboxCreationOptions)`; `createSandbox(defaultFlavorSpec: string, options)` where spec = `"2:gvisor"` / `"3:macSandboxExec,docker"`.
**Data Shape:** `SandboxProcess = { name, child?, control(): ISandboxControl, dataTo/FromSandboxDescriptor?, getData?, sendData? }`; flavors keyed by name incl. aliases `skip→unsandboxed` and `sandboxed` (probe-order composite).

### Decisive source
```ts
function sandboxed(options: ISandboxOptions): SandboxProcess {
  if (hasRunsc)       { return gvisor(options); }
  if (hasSandboxExec) { return macSandboxExec(options); }
  return pyodide(options);          // runs anywhere node/deno runs
}
// flavor selection: env override wins, then comma list filtered by python version
const flavors = (getSandboxFlavor() || defaultFlavorSpec).split(",");
... if (preferredPythonVersion === version || version === "*") return createConcreteSandbox(flavor, options);
// command resolution precedence:
process.env["GRIST_SANDBOX" + pythonVersion] || process.env.GRIST_SANDBOX || creator default
```

**Flow:** creator normalizes options (minimalPipeMode true, deterministicMode from LIBFAKETIME_PATH, entry point default `grist/main.py`) → chosen spawner builds a command line via FlagBag (`-E/--env` env vars, `-m/-v` mounts) → mounts engine read-only + importDir, injects `PIPE_MODE`, optional DETERMINISTIC_MODE/faketime wrap → spawns through `adjustedSpawn` (honors `GRIST_SANDBOX_OOM_SCORE_ADJ` via `choom -n`) → returns control object: DirectProcessControl (unsandboxed/mac), SubprocessControl with label recognizers for gvisor ptrace (`exe`+`exe` parent traced; `runsc-sandbox` managed), NoProcessControl (docker/checkpoint). Docker adds `--network none --rm -i`; mac builds a deny-default sandbox-exec profile allowing exactly the resolved python symlink chain + `/usr/local` + `/opt/homebrew` + Grist dirs. Availability is probed by PATH lookup only ("doesn't check that those commands actually work") — `testSandboxFlavor` does a REAL create→`get_version`→shutdown lifecycle with 5s timeout and reports `lastSuccessfulStep`.
**Invariant:** all flavors speak the SAME pipe protocol so NSandbox above is flavor-blind; faketime placement differs by flavor (LD_PRELOAD/DYLD wrap only works unsandboxed — gvisor/docker need in-sandbox faketime); 5-pipe mode throws in every flavor except unsandboxed; paths stay host-real ("leaks host directory names" — accepted trade to keep nesting wrappers possible). `GRIST_CHECKPOINT_MAKE` suppresses the close-event handler (checkpoint exit is expected) and returns NoProcessControl.
**Probe:** `test/server/Sandbox.ts:87/:99` create `createSandbox("sandboxed", {})` and run real engine user actions (:89–109); flavor matrix unit-pinned indirectly via `test/server/lib/gristSettings.ts` getSandboxFlavor tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "NSandboxCreator createSandbox gvisor docker macSandboxExec FlagBag", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the SpawnFn-table pattern for any pluggable isolation backend (code runners, formula engines); adopt the capability-probe fallback order and the create/use/shutdown smoke test before trusting a backend. Adapt flag syntax per backend through a FlagBag-equivalent rather than string soup; keep env allowlists explicit (PIPE_MODE/DETERMINISTIC_MODE). Omit mac profile minutiae (brew-specific subpaths) and gvisor ptrace recognizers unless targeting those exact runtimes.
