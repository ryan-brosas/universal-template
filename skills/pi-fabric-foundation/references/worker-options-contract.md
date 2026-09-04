<!-- capsule-v2 -->
# Worker argv options contract — how does a spawned child parse its entire launch configuration from strict flag/value pairs, and what happens on any deviation?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the exact worker-side schema for `argv` coming from a transport launch, which fields are mandatory, and how are complex values (JSON arrays) carried?

## Strict even-slot flag parser with required/optional lanes and runner whitelist
**Path/Symbol:** `src/worker/options.ts` whole file (95L): `argumentMap` (:3-14), `required` (:16-20), `optional` (:22-23), `parseWorkerOptions` (:25-95). Consumer: `src/worker.ts:236` (`optionHelpers.parseWorkerOptions()`). Type source: `AgentWorkerOptions` in `src/agents/types.ts`. Direct tests: `tests/worker-e2e.test.ts` exercises the full argv through real manager launches.
**Signature:** `parseWorkerOptions(argv: readonly string[] = process.argv): AgentWorkerOptions`.
**Data Shape:** map of `--flag value` pairs; REQUIRED: `id`, `runner`, `name`, `task-file`, `status-file`, `lifecycle-file`, `log-file`, `cwd`, `pi-binary`, `claude-binary`, `veda-binary`, `veda-backend`, `veda-persona`, `timeout-ms`, `depth`, `full-code-mode`, `extensions`, `tools` (JSON array), `granted-risks` (JSON array), `transport`; OPTIONAL: `model`, `thinking`, `fabric-extension`, `schema-file`, `images-file`, `system-prompt`, `session-file`, `actor-id`, `actor-name`, `mesh-root`, `project-root`, `owner-host-id`, `owner-identity-id`, `run-root`, `steer-file`, `branch`, `worktree`, `max-tokens`, `main-agent-id`.

### Decisive source
```ts
// argv[0]=runtime argv[1]=worker.js → pairs start at index 2
for (let index = 2; index < argv.length; index += 2) {
  const key = argv[index];
  const value = argv[index + 1];
  if (!key?.startsWith("--") || value === undefined)
    throw new Error(`Invalid worker argument near ${key ?? "<end>"}`);   // odd count / bare token
  result.set(key.slice(2), value);
}
const runner = required(args, "runner");
if (runner !== "pi" && runner !== "claude" && runner !== "veda")
  throw new Error(`Unsupported Fabric agent runner: ${runner}`);
```

**Flow:** every option is a two-cell pair — NO boolean flags without values, NO `--flag=value` syntax, NO repeated flags (last wins via Map.set). Numeric fields are converted at parse time (`Number(required(...))`), booleans compare the literal string `"true"`, and structured values arrive as JSON strings parsed inline: `JSON.parse(required(args, "tools"))` and `"granted-risks"` (:74-75). Optional flags normalize empty-string to undefined via `args.get(name) || undefined`. The result feeds `createRunningRecord` so status.json mirrors exactly what the child was launched with (including transport and branch/worktree).
**Invariant:** malformed argv throws BEFORE any side-effectful work (no files created, no session opened) — a child that cannot parse its launch config must die loudly at boot rather than run with defaults; the runner whitelist is enforced here at the worker boundary IN ADDITION to manager-side coercion (defense in depth across the process boundary); `transport` is passed through unvalidated here because the manager already resolved it against available adapters.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-ecosystem/pi-fabric && grep -c "required(args" src/worker/options.ts'` → 20; `grep -n "Unsupported Fabric agent runner" src/worker/options.ts | wc -l` → 1 (:51); `grep -n "Invalid worker argument near" src/worker/options.ts | wc -l` → 1 (:9); `grep -cF "JSON.parse(required" src/worker/options.ts` → 2; `grep -n "index = 2" src/worker/options.ts | wc -l` → 1 (:5).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "parseWorkerOptions argument map required optional", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #1-4 resolve `argumentMap` :3-14, `required` :16-20, `optional` :22-23, `parseWorkerOptions` :25-95 line-exact.)

## Verdict
Adopt the even-slot pair grammar with loud parse-time death for any spawned-worker CLI contract, plus boundary-side runner whitelisting; adapt the field roster to your runner's needs; omit JSON-array flags if your argv budget allows response files instead. Coverage caveat: no unit spec imports this module directly — behavior pinned end-to-end by `tests/worker-e2e.test.ts` real-launch suites.
