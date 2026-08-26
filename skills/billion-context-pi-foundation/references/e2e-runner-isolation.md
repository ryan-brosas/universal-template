<!-- capsule-v2 -->
# E2E runner isolation — how do you run a REAL agent CLI headlessly in a throwaway HOME and map scenario turns onto process invocations?

**Source:** billion-context-pi (MIT) `master@6a88c5565355`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How must a porter isolate full-pipeline regression runs from the developer's machine and from prior runs, deterministically?

## per-scenario temp HOME (HOME+USERPROFILE) + merged config + one invocation per non-auto turn + sync health bridge
**Path/Symbol:** `scripts/e2e/run-e2e.mjs`: env knobs (:33-38), signal-safe cleanup (:56-74), `resolvePiBin` (:76-90), sync sleep/probe bridges (:53-54, :107-128), `writePiConfig` (:130-153), `applyScenarioAcpConfig` (:155-161), `userTurns` auto-filter (:163-173), `newestStateFile` (:175-185), `runPiTurn` (:187-229), `runScenario` (:231-333), build+dispatch `main` (:335-402).
**Signature:** `node scripts/e2e/run-e2e.mjs [scenario-substring]`; env: `PI_BIN` (or node_modules dist cli.js), `BCP_E2E_EXTENSION`, `FAKE_LLM_PORT` (8400), `BCP_E2E_WORK_ROOT` (tmpdir/bcp-e2e).
**Data Shape:** per-scenario workspace under WORK_ROOT: `home-<name>/` (isolated HOME), `sessions-<name>/` (--session-dir), `turn-<name>` (counter file), `obs-<name>.json` (observations), `pi-<name>.log`, `fake-<name>.log`; result artifact = newest `.acp.json` in the session dir.

### Decisive source
```ts
// :208-213 — os.homedir() reads $HOME on POSIX but %USERPROFILE% on Windows;
// setting BOTH makes one isolation recipe cross-platform:
const env = { ...process.env, HOME: home, USERPROFILE: home, PI_OFFLINE: "1" };

// :107-116 — async waitFor would rework the whole runner; a spawnSync CHILD
// bridges synchronous probing (50 x 200ms attempts, 1s http timeout each):
const req = http.get("http://127.0.0.1:" + process.argv[1] + "/v1/models", (res) => {
  res.resume(); process.exit(res.statusCode === 200 ? 0 : 1); });
```

**Flow:** build once (`npm run build`, verify dist/index.js exists), then per scenario: wipe + recreate home/sessions dirs, write empty counter + observations + logs; write `<home>/.pi/agent/models.json` registering provider `fake` at `http://127.0.0.1:8400` (`api: openai-completions`, model fake-model, contextWindow 100000, `compat.supportsStrictTools:false`) and base `<home>/.pi/acp.json` `{autoUpdate:false, debug:false}` shallow-merged (`Object.assign`) with the scenario's `acpConfig`; spawn fake-llm-server.cjs with SCENARIO/TURN_COUNTER/OBSERVATIONS/PORT env; poll health synchronously; then iterate ONLY non-auto turns — each spawns ONE real `pi -p --mode json --provider fake --model fake/fake-model --api-key fake -ne -e <extension> --session-dir <dir>` with `-c` appended after the first turn (continues the same session) and the user message positional last; `auto:true` turns are tool-follow-ups consumed INSIDE the previous invocation and never spawn anything. After the loop: pick the NEWEST-mtime `.acp.json` from the session dir and hand it to verify.mjs together with scenario path + session dir + OBSERVATIONS env.
**Invariant:** (1) isolation is total — HOME/USERPROFILE redirection means config, sessions, and state all land under the scenario workspace; nothing touches the developer HOME. (2) Turn mapping is deterministic: one user turn == exactly one CLI process; follow-up tool turns ride inside it. (3) `-c` after the first invocation is what makes multi-invocation runs ONE session (and thus one persisted state file). (4) Newest-mtime selection tolerates pi creating timestamped session files. (5) The fake server dies on exit/SIGINT/SIGTERM via registered cleanup (:56-74).
**Probe:** executed this pass: `npm run e2e -- 01-basic` from the repo root (build + real pi -p against the fake server + verify.mjs) — result recorded honestly in verification.md. Static probes: node --check on the runner; grep-verified PI_OFFLINE/HOME/USERPROFILE wiring above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "e2e runner scenario isolated HOME session-dir pi -p", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: dual-HOME-var isolation, config merge order (base defaults then scenario override), one-process-per-user-turn with -c continuation, synchronous child-bridge health polling, and newest-mtime artifact discovery when porting headless agent E2E rigs. Adapt provider registration shape and CLI flags to your host. Omit ANSI color plumbing (cosmetic).