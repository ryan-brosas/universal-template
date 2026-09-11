<!-- capsule-v2 -->
# Resume-config recovery — how to relaunch a benchmark job exactly without re-specifying its flags

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When a long benchmark run died halfway, how do you rebuild the original invocation from disk so a resume needs nothing re-specified — and which knobs belong to the resume call instead?

## Snapshot-at-launch with fallback ladder, recorded-backend override
**Path/Symbol:** `packages/metaharness/src/runner.ts`:`resolveResumeConfig` (391-437), `buildResumeArgs` (1346-1353), snapshot write in `runBenchmark` (1560-1564); request→argv mapping `src/launch-args.ts`:`harborRunnerArgs` (48-84).
**Signature:** `function resolveResumeConfig(cli: Config): Config`; `function buildResumeArgs(cfg: Config, jobDir: string): string[]`; `harborRunnerArgs(request: LaunchRequest, opts: { jobsDir; jobName; dataset }): string[]`.
**Data Shape:** two on-disk records per job: `_bench/<job>/runner-config.json` = full resolved `Config` snapshot written at launch; `<job>/manager.json` = API launch record `{benchmark, dataset, config: LaunchRequest}`; `<job>/config.json` = the executor's own recorded runtime config (decides container backend). Resume spec is a bare name (under `jobsDir`) or any path.

### Decisive source
```ts
const saved = readJson(path.join(jobsDir, "_bench", jobName, "runner-config.json"));
if (saved && typeof saved === "object") {
    cfg = { ...defaultConfig(), ...(saved as Partial<Config>) };
} else {
    const manager = readJson(path.join(jobDir, "manager.json"));
    if (manager?.config) {
        // rebuild runner argv from the launch record, re-parse into Config
        cfg = parseArgs(harborRunnerArgs(manager.config, { jobsDir, jobName, dataset }));
    }
}
...
// The recorded backend wins over any reconstruction-time preference
// (e.g. apple-container auto-detection added after the original run).
const recorded = jobConfig.environment?.type;
if ((recorded === "docker" || recorded === "apple-container") && cfg.envType !== recorded) {
    if (recorded === "apple-container" && cfg.gatewayUrl === DOCKER_GATEWAY_URL) cfg.gatewayUrl = VMNET_GATEWAY_URL;
    else if (recorded === "docker" && cfg.gatewayUrl === VMNET_GATEWAY_URL) cfg.gatewayUrl = DOCKER_GATEWAY_URL;
    cfg.envType = recorded;
}
// Knobs owned by the resume invocation, not the original launch.
cfg.filterErrorTypes = cli.filterErrorTypes; cfg.passthrough = cli.passthrough;
cfg.dryRun = cli.dryRun; cfg.cleanup = cli.cleanup; cfg.cleanupForce = cli.cleanupForce;
```

**Flow:** at launch, the runner snapshots its fully-resolved Config to `_bench/<name>/runner-config.json` → on `--resume <name|path>`: locate the job dir (path spec ⇒ dirname/basename), require the executor's `config.json` (else "not a harbor job dir") → restore Config from the exact snapshot; else rebuild argv from `manager.json`'s LaunchRequest via the shared request→argv function and re-parse; else fail loudly ("no recorded launch config") → force the recorded container backend (swapping the default gateway host with it) → overlay only resume-invocation knobs (error-type filters, passthrough, dry-run/cleanup) from the CLI → `buildResumeArgs` emits the executor's resume command; when explicit `-f` error filters are given, harbor's `CancelledError` default is ALWAYS re-added alongside them.
**Invariant:** the recorded runtime config beats reconstruction-time preferences (a run started on docker must resume on docker even if auto-detection would now choose apple-container); retry-set replacement never silently drops the executor's built-in default filter (`CancelledError`); an unresumable dir fails loudly rather than guessing.
**Probe:** `packages/metaharness/test/runner.test.ts:181-290` — `recovers the full launch config from manager.json`, `prefers the runner-config.json snapshot and forces the recorded container backend`, `rejects a job dir without a recorded launch config or without harbor's config.json`, and `re-adds harbor's CancelledError default when explicit -f filters would replace it`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveResumeConfig buildResumeArgs harborRunnerArgs runner-config manager.json", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-record pattern (exact snapshot → launch record → loud failure) plus the recorded-environment-wins rule and the always-re-add-default-filter rule for any resumable job system. Adapt the flag names, backend enum, and gateway-URL swap to your stack; omit the docker/apple-container specifics. Four direct tests pin the ladder, the override, and the filter union.
