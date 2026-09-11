<!-- capsule-v2 -->
# pi binary resolution ladder — how does a minimal-PATH daemon find and correctly spawn `pi`?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** The daemon's PATH lacks user-installed binaries — where does `pi` come from, and which PATH must it be spawned WITH?

## Daemon PATH scan → login-shell PATH probe; spawn PATH ≠ daemon PATH
**Path/Symbol:** `packages/server/src/pi-binary-resolver.ts:resolvePiAndPath` (:69–83) + `resolveLoginPath` (:47–67).
**Signature:** `resolvePiAndPath(shimsDir: string, override?: string): { binary: string|null, pathEnv: string }`.
**Data Shape:** `cachedPi` caches only SUCCESSFUL resolutions (null re-resolves each call, so a later install is picked up); login-shell probe = `$SHELL -l -i -c 'printf PIPATHBEGIN%sPIPATHEND "$PATH"'` with empty stdin + 10s timeout; marker slicing survives OSC-7-style stdout noise from shell hooks.

### Decisive source
```ts
const fromDaemon = scanPathForPi(daemonPath, shimsDir);
  if (fromDaemon) {
    cachedPi = { binary: fromDaemon, pathEnv: pathWithoutShims(daemonPath, shimsDir) };
    return cachedPi;
  }
  const loginPath = resolveLoginPath();
```

**Flow:** explicit test override short-circuits everything → cached resolution → scan daemon PATH dir-by-dir (statSync+accessSync X_OK per candidate, skipping the shims dir) → miss ⇒ probe the user's LOGIN INTERACTIVE shell for its RC-augmented PATH → scan that (minus shims). Spawn uses `pathEnv || process.env.PATH` so pi and its tools (node, git) resolve.
**Invariant:** TWO traps a porter will hit: (1) the shims dir must be stripped BOTH from the search and from the spawn PATH — localterm's secret-injecting shims shadow real binaries by name (`pi` included), and leaving them in would double-inject secrets the automation already passed as env; (2) the spawn PATH is the RESOLVED source's PATH (login PATH when found via login shell), NOT the daemon's minimal one — spawning with the daemon PATH leaves pi unable to run node/git. Only success is cached; failure re-probes next run.
**Probe:** `packages/server/tests/agent-runner.test.ts` (`reports a clear message when pi is not on PATH` :255–272 — PATH=empty tmpdir AND SHELL=/nonexistent defeats the login fallback, asserting the genuine not-found path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "resolvePiAndPath login shell PATH shims", limit: 10 });
```

## Verdict
Adopt the two-source ladder, cache-success-only policy, shims-stripping, and resolved-source spawn PATH; adapt the shell probe to your platform shells (zsh default here). Directly tested for the not-found path; happy path covered via piBinaryPath override tests.
