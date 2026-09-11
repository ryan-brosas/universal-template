<!-- capsule-v2 -->
# Child spawn mechanics — how are delegate children launched so recursion is bounded, the CLI is found on any host, tools are soft-restricted, and mode fits both host and session?

**Source:** billion-context-pi (MIT) `master@6a88c5565355`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How must a porter build child agent args (depth gate, executable resolution, stdin task, tool allowlist, mode selection), and how does the reply plane differ per host?

## env depth counter + CLI-entry ladder + stdin task + soft --tools allowlist + host-aware mode
**Path/Symbol:** `src/delegate-tool.ts`: `buildChildArgs` (:908-953), `resolvePiCliEntry` (:73-90) with `PI_CLI_ENTRY_RE` (:42), `probeUpFromArgv` (:45-54), `piCliGlobalCandidates` (:56-67), spawn wiring in `runDelegate` (:654-694; depth gate :658-661, env increment :669, spawn :685-689, `child.stdin.end(args.task)` :694), watchdog attach (:704-718), error-path finalize (:857-879); `src/runtime.ts`: `isPiHost` (:37-40).
**Signature:** `buildChildArgs(args, rolePrompt, ctx) -> {cliArgs, tmpDir, isAsync, useJsonStream}`; `resolvePiCliEntry(argv1, env?, piHost?) -> string`; child = fresh `<process.execPath> <resolved-cli-entry>` of the parent.
**Data Shape:** role prompt written to a tmp `role.md` under `mkdtemp("acp-delegate-")` passed as `--append-system-prompt`; always `--no-session`; two stream files per run under `tmpdir()/acp-delegate`: `<runId>.out` (reply) and `<runId>.activity` (tool activity; pi json mode only — the CHILD is told only about the activity file).

### Decisive source
```ts
// :926-930 — mode is a 2x2 of session shape x host capability:
const isAsync = args.async !== false && ctx.mode !== "print" && ctx.mode !== "json";
const useJsonStream = isAsync && isPiHost(ctx.sessionManager);
const cliArgs = useJsonStream
  ? ["--mode", "json", "--no-session", "--append-system-prompt", promptFile]
  : ["-p", "--no-session", "--append-system-prompt", promptFile];

// :78-89 — CLI entry ladder; argv[1] lies under embedded hosts:
const explicit = env.PI_CLI_PATH;
if (explicit) return explicit;
if (argv1 && PI_CLI_ENTRY_RE.test(argv1)) return argv1;
if (piHost) { const probed = probeUpFromArgv(argv1); if (probed) return probed;
  for (const candidate of piCliGlobalCandidates(env)) { if (existsSync(candidate)) return candidate; }
  logWarn("delegate", { event: "cli-entry-unresolved", argv1, fallback: "argv[1]" }); }
return argv1;
```

**Flow:** depth gate reads `PI_ACP_DELEGATE_DEPTH` from env and refuses at MAX_DEPTH=2 (:23, :658-661) — recursion bound travels in ENV because wrapper shells break process-lineage detection; the same key incremented by 1 goes into the child env (:667-670). Executable resolution (:73-90): `PI_CLI_PATH` env -> argv[1] matching the `pi-coding-agent/dist/cli.js` path-suffix regex -> upward probe from `dirname(argv[1])` for `node_modules/@earendil-works/pi-coding-agent/dist/cli.js` (pi-host only) -> global candidates (Windows `%APPDATA%/npm/node_modules/...`; unix `$HOME/.local/lib`, `/usr/local/lib`, `/usr/lib`) -> give up with a warn and fall back to argv[1] untouched. Non-pi hosts keep argv[1] unmodified at every step (`isPiHost` = capability sniff for `sessionManager.buildContextEntries`, runtime.ts :37-40). Restricted roles (`reviewer/researcher/planner/oracle`) get `--tools read,bash,grep,find,ls` merged with ACP_TOOLS dedup'd (:937-941); WORKER intentionally gets NO --tools so all extension/custom tools stay active for primary-task delegation (:96-99). Explicit `model:"provider/id"` splits on the first "/"; otherwise inherit the parent's current provider/model (:943-950). Async downgrades to sync in one-shot sessions (print/json) because injection needs a follow-up turn those modes never observe (:672-680 logs it). Reply planes: async+pi streams `--mode json` events through `makeEventApplier`; async-on-omp has NO json mode, so stdout IS the reply — chunks go to `EventApplier.appendRaw` (:223-229 interface, :307-310 impl) with no line buffering and NO `.activity` file (:719-724). Spawn-error path MUST finalize manually — Node does not guarantee `close` after `error` (EPIPE/ENOENT): settled-guarded handler disposes watchdogs, removes files, sets failed/cancelled + synthetic body, wakes the waiter (:857-879); forgetting this orphans the run forever in "running".
**Invariant:** recursion bound travels in ENV, not lineage; the allowlist is an honesty-framed convenience guardrail ("prevents ACCIDENTAL edit/write ... not a security boundary") never claimed as isolation; one-shot hosts get sync delegation only; embedded hosts must probe for the real CLI before trusting argv[1]; every spawn must pair `close` handling with an `error` finalize.
**Probe:** `tests/delegate-tool.test.ts` — shell:false spawn options for Windows paths (:18-23); --tools composition/order/no-duplicates per restricted role (:34-64); worker and unknown agents omit --tools, worker still inherits model (:68-100); --tools placed before --provider/--model (:104-114); ctx.model inheritance vs explicit override (:118-146); mode matrix: --mode json on pi async / -p fallback on omp async / -p kept for sync even on pi (:184-217).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "buildChildArgs resolvePiCliEntry appendRaw PI_ACP_DELEGATE_DEPTH", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: env-based depth gate, staged CLI-entry resolution with an honest fallback warn, stdin task delivery, tmp role prompt, manual finalize on spawn error, async->sync downgrade on one-shot hosts, capability-sniffed host detection, and the dual reply-plane split (event stream vs raw stdout). Adapt flag spellings, global install paths, and event schema to your host CLI. Omit per-role allowlist tables (data, not contract).
