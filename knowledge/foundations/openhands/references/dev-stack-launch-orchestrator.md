<!-- capsule-v2 -->
# Local dev-stack launch orchestrator — fail-fast port preflight, versioned uvx server ladder, and stale-lease cleanup gated on liveness

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How does an npm-launched "full stack" script start a Python agent-server + Vite frontend so concurrent instances, cached wheels, reaped tmp dirs, and hard-killed predecessors cannot corrupt the run?

## Connected graph-selected seam
**Path/Symbol:** `scripts/dev-safe.mjs` (1197 L): `buildAgentServerCommand` (423–524), `assertPortsFree` (266–285), `findFreePorts` (296–330), `getOrCreatePersistedApiKey` (148–180), `buildAgentServerEnv` (776–823), `buildNpmScriptCommand` (830–861), `waitForServer` (882–899) raced against backend error/exit (1052–1061), shutdown ladder (1009–1032), `isPortBusy` (1117–1133), `releaseStaleConversationLeases` (1157–1182). Direct test: `__tests__/scripts/dev-safe.test.ts` (`describe("assertPortsFree")` :235+, `describe("buildAgentServerCommand")` :462+; also `vscode-base-path-opt-in.test.ts` enforcing the env/route pairing).
**Signature:** `buildAgentServerCommand(env): { command:"uvx", args:string[], source:string }`; `assertPortsFree([{name,port}]): Promise<void>` throws; `releaseStaleConversationLeases(dir): number`.
**Data Shape:** source ladder strings `local (<path>)` | `git (<ref>)` | `PyPI (<version>)` | `PyPI (<version>, default)`; config from `config/defaults.json` (`SHARED_DEFAULTS.ports/packages/versions/paths/constraints`).

### Decisive source
```js
// Source ladder: local checkout > git ref > explicit PyPI version > default PyPI.
// ALL FOUR SDK packages always pinned to the SAME ref/version so inter-package APIs stay in sync:
if (gitRef) uvxArgs.push("--reinstall", "--from", `git+${REPO}@${gitRef}#subdirectory=openhands-agent-server`,
  "--with", `git+${REPO}@${gitRef}#subdirectory=openhands-sdk`, ..., "agent-server");
// --reinstall is REQUIRED on the git path: a branch may carry the same version string as the
// current PyPI release; without it uv silently reuses cached PyPI wheels and the ref is never used.
// Fail-fast preflight BEFORE spawning — detect a second instance instead of drifting to new ports:
const busy = results.filter(({ free }) => !free);
if (busy.length) throw new Error(`Cannot start: the following ports are already in use:\n\n${lines}\n\nAnother agent-canvas instance may already be running.`);
// Stale-lease cleanup: owner_lease.json locks each conversation dir to one server (45 s TTL heartbeat).
// Hard kill leaves leases; a NEW server then skips every conversation (search returns [] though files exist).
// Caller MUST verify isPortBusy(backendPort) === false first — no other way to tell stale from renewed.
for (convDir of readdirSync(conversationsDir)) if (existsSync(join(convDir,"owner_lease.json"))) { try { unlinkSync(...); removed++; } catch {} }
```

**Flow:** validate frontend bins (`node_modules/.bin/cross-env|react-router`, win32 adds `.cmd/.ps1` candidates) → allocate/preflight ports → build server command by ladder → mkdir state tree under `~/.openhands/agent-canvas` → spawn uvx agent-server with `buildAgentServerEnv` (`PYTHONUTF8=1` for cp1252-emoji crashes; `TMUX_TMPDIR=<stateDir>/tmux` because macOS reaps os.tmpdir() sockets while live; persisted 0600 api-key/secret-key files keep Vite-baked key, server env, and localStorage registry in sync across restarts; `OH_VSCODE_BASE_PATH` is an EXPLICIT opt-in so every caller must also register the matching ingress route — test-enforced pairing) → `Promise.race(waitForServer("/server_info"), backendErrored, backendExited)` so exit-before-startup rejects fast → spawn frontend via `buildNpmScriptCommand` (win32 ALWAYS cmd.exe: npm_execpath paths with spaces split under shell:true) → idempotent `shutdown()`: signal both process trees, SIGKILL after 3 s grace.

**Invariant:** Preferred-port check is documented check-then-use (bind race accepted; services must handle EADDRINUSE; Vite strictPort fails fast); multi-port allocation is sequential with a used-set + 100-attempt cap so the allocator never races itself; lease deletion is best-effort and liveness-gated; key material degrades to in-memory with a warning rather than failing startup.

**Probe:** Executed this pass under `node --input-type=module -e` importing the REAL `dev-safe.mjs` (exit 0): default ladder → `PyPI (1.42.1, default)` pinning all four SDK packages + acp constraint; git-ref path includes `--reinstall`; version override emits `--from openhands-agent-server==1.42.0`; relative `OH_AGENT_SERVER_LOCAL_PATH` throws; `isPortBusy` true-while-listening/false-after-close; `assertPortsFree` on the busy port throws the named-instance message; `findFreePorts` returns distinct ports; `releaseStaleConversationLeases` unlinks exactly the in-directory lease (plain file ignored); API key stable across cache reset, 64-hex, mode 0600.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_architecture({ project: "openhands", path: "scripts", aspects: ["file_tree"] });
// executed this pass -> 25 scripts incl. dev-safe.mjs, dev-with-automation.mjs, proxy-utils.mjs, runtime-services-info.mjs
await mcp.codebase_memory.check_index_coverage({ project: "openhands", paths: ["scripts/dev-safe.mjs", "__tests__/scripts/dev-safe.test.ts"] });
// executed this pass -> no_recorded_issue ×2
```

## Verdict
Adopt the four-layer posture: named fail-fast port preflight (vs silent drift), same-ref-everywhere dependency ladders with the --reinstall-for-git-refs rule, home-dir-persisted 0600 secrets shared across launch modes, and liveness-gated stale-lock cleanup with documented TTL rationale. Adopt the explicit-opt-in trick for any advertised URL that needs a paired route. Adapt uvx/package names, port names, and tmux specifics to your stack; omit PostHog telemetry plumbing. Windows cmd.exe/npm_execpath handling ports as-is. Coverage: `no_recorded_issue` ×2; behavioral probe executed live against real source as recorded.
