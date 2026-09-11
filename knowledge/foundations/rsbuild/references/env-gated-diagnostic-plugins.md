<!-- capsule-v2 -->
# Env-gated diagnostic plugins — how do progress, Rsdoctor, and Rspack profiling opt in without config surface?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `rsbuild`. **Question:** a porter adding opt-in build diagnostics must reproduce three different gating styles: config-object with default-prefix spread, late-binding optional-dependency injection, and env-preset trace registration with terminal-output rules.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/progress.ts:pluginProgress` (3–25); `packages/core/src/plugins/rsdoctor.ts:pluginRsdoctor` (14–78); `packages/core/src/plugins/rspackProfile.ts` — `applyProfile` (46–96), `pluginRspackProfile` (100–140), `resolveLayer` (21–33).
**Signature:** all three are `(): RsbuildPlugin`; profile gates on `process.env.RSPACK_PROFILE`, doctor on `process.env.RSDOCTOR === 'true'`, progress on normalized `config.dev.progressBar`.
**Data Shape:** progress options `{ id?, …rspack.ProgressPlugin options } | false`; doctor injects `new RsdoctorRspackPlugin()` into EVERY bundler config; profile filter is an EnvFilter string (`OVERVIEW→'info'`, `ALL→'trace'`, raw passthrough).

### Decisive source
```ts
// progress: computed prefix is only a DEFAULT — the user object spread comes AFTER
const prefix = options !== true && options.id !== undefined ? options.id : environment.name;
chain.plugin(CHAIN_ID.PLUGIN.PROGRESS).use(rspack.ProgressPlugin, [
  { prefix, ...(options === true ? {} : options) },
]);
```
```ts
// rsdoctor: env gate checked at onBeforeCreateCompiler — mutates GENERATED bundlerConfigs
if (process.env.RSDOCTOR !== 'true') return;
const registered = config.plugins?.some((p) =>
  p?.isRsdoctorPlugin === true || p?.constructor?.name === 'RsdoctorRspackPlugin');
if (registered) return;                                  // dedupe against manual registration
try { packagePath = require.resolve('@rsdoctor/rspack-plugin', { paths: [api.context.rootPath] }); }
catch { api.logger.warn('…please install @rsdoctor/rspack-plugin package.'); return; }   // optional peer, fail-soft
module = await import(isWindows ? pathToFileURL(packagePath).href : packagePath);
for (const config of bundlerConfigs) { config.plugins ||= []; config.plugins.push(new module[pluginName]()); }
```
```ts
// rspackProfile: preset → EnvFilter, terminal output ONLY for logger layer, per-process output dir
if (traceLayer !== 'perfetto' && traceLayer !== 'logger') throw new Error(`unsupported trace layer: ${traceLayer}`);
if (traceOutput && traceLayer === 'perfetto' && isTerminalTraceOutput(traceOutput)) throw new Error(
  'RSPACK_TRACE_OUTPUT=stdout|stderr is only supported for the logger trace layer. …');
const defaultOutputDir = path.join(root, `.rspack-profile-${Date.now()}-${process.pid}`);
if (!traceOutput) traceOutput = path.resolve(defaultOutputDir,
  traceLayer === 'perfetto' ? DEFAULT_RUST_TRACE_PERFETTO_OUTPUT : DEFAULT_RUST_TRACE_LOGGER_OUTPUT);
await rspack.experiments.globalTrace.register(resolveLayer(RSPACK_PROFILE), traceLayer, traceOutput);
// lifecycle: register once at onBeforeBuild(isFirstCompile) or onBeforeStartDevServer;
api.onExit(() => { if (!traceOutput) return; void rspack.experiments.globalTrace.cleanup();   // fire-and-forget flush
  if (!isTerminalTraceOutput(traceOutput)) api.logger.info(`profile file saved to ${color.cyan(traceOutput)}`); });
```

**Flow:** three escalation levels of invasiveness: progress decorates the chain during config build; doctor waits until configs EXIST then appends instances across environments (skipping when any env already registered); profile registers a process-global tracer just before first compile / dev start and unregisters via `cleanup()` on exit without awaiting.

**Invariant:** diagnostics must never change build semantics by default — every gate defaults OFF; doctor's dedupe check runs across ALL bundler configs before injecting anywhere; profile's stdout/stderr outputs bypass the default dir entirely and skip the "saved to" log.

**Probe:** No unit suites exist for these three files at pin (grep over `packages/core/tests` executed — zero matches for RSPACK_PROFILE/rsdoctor/progressBar outside snapshots). Deterministic source pins executed byte-for-byte: `...(options === true ? {} : options),` progress.ts:23; `process.env.RSDOCTOR !== 'true'` rsdoctor.ts:20; `void rspack.experiments.globalTrace.cleanup();` rspackProfile.ts:132.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginRsdoctor applyProfile globalTrace register ProgressPlugin prefix", limit: 10 });
```
Executed pre-reindex: `pluginRsdoctor` 14–78, `applyProfile` 46–85, `pluginProgress` 3–25 served line-exact vs direct reads.

## Verdict
Adopt the three gating idioms (config-default-spread, generated-config injection with cross-env dedupe + fail-soft optional peer resolution from the PROJECT root, preset-filtered process-global tracing). Adapt the concrete plugin names/packages to your stack. Omit the Windows file-URL dance only if your host is POSIX-only. Coverage caveat: no direct tests at pin — behavior pinned by source reads + executed grep probes.
