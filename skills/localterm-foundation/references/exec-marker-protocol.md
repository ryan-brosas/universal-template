<!-- capsule-v2 -->
# In-PTY exec marker protocol — how do you run a command in a SHARED interactive shell and recover its output and exit code when you control neither echo nor the prompt?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How can an agent execute one command inside a persistent, possibly-viewed PTY session and get clean rendered output plus a reliable exit code?

## Marker-wrapped single-line exec over the live PTY
**Path/Symbol:** `packages/server/src/session-command-executor.ts:SessionCommandExecutor.execute` (:116–219); `buildExecResult` (:221–260). Exposed as `SessionManager.execInSession` (`session-manager.ts`:768–777) behind `POST /sessions/:id/exec` (`index.ts`:886–900, body validated by `execInputSchema`, `schemas.ts`:222–228).
**Signature:** `execute(managed: ManagedSession, command: string, options?: ExecOptions): Promise<ExecResult>` where `ExecResult = { exitCode: number | null; output: string; timedOut: boolean; truncated: boolean; durationMs: number }`.
**Data Shape:** options clamp via `clampInt` to `timeoutMs ∈ [1, EXEC_MAX_TIMEOUT_MS=30*60_000]` (default `EXEC_DEFAULT_TIMEOUT_MS=120_000`), `outputLimitBytes ∈ [1, EXEC_MAX_OUTPUT_LIMIT_BYTES=8MB]` (default 1MB) — constants.ts:873–880. Raw accumulation is capped separately at `EXEC_RAW_ACCUMULATE_CAP_BYTES=16MB`. Empty/whitespace command becomes `:` (no-op).

### Decisive source
```ts
// :134-139 — random token brackets the command on ONE input line
const token = randomBytes(8).toString("hex");
const startMarker = `__LT_S_${token}__`;
const endMarkerPrefix = `__LT_E_${token}__`;
const endPattern = new RegExp(`${endMarkerPrefix} (\\d+)`);
const wrapped = `printf '${startMarker}\n'; ${cmd}; printf '${endMarkerPrefix} %d\n' "$?"`;
...
// :202-212 — timeout COMMITS, interrupts, then honors a grace window
didTimeout = true;
session.write("\x03");                       // Ctrl-C: return the PTY to a prompt
interruptHandle = setTimeout(() => finalize(null, true), EXEC_TIMEOUT_INTERRUPT_GRACE_MS); // 500ms
```

**Flow:** write `wrapped + "\r"` to the shared PTY (:217) → every `output` event appends to `accumulated` until the 16MB raw cap (`capped` latch stops further growth but output still streams) → regex-matching `__LT_E_<token> <code>` in the RAW stream resolves the exec with that exit code (a normal completion typically resolves BEFORE any shell exit event) → `finalize` detaches listeners, then `buildExecResult` renders the raw stream through a FRESH headless `CaptureRenderer(cols, rows, EXEC_EPHEMERAL_SCROLLBACK=10_000)` (:236), `findRow(startMarker)`/`findRow(endMarkerPrefix + " " + exitCode)` (-1 fallbacks) bracket `extractBetween` for clean ANSI-processed output, renderer disposed in `finally`; truncation to `outputLimitBytes` happens LAST, UTF-8-byte-exact via Buffer subarray (:248–252). On `timeoutMs`: commit `didTimeout=true` → Ctrl-C → resolve after 500ms grace with partial output; markers arriving during the grace are IGNORED (:187–188) so the call stays `timedOut`. Shell `exit` event is the fallback resolver (dead session ⇒ its real exit code).

**Invariant:** the exit code is recovered by parsing the embedded end-marker out of the raw output stream — never from prompt scraping or shell lifecycle events; the whole protocol rides ONE `;`-chained input line precisely so `$?` is still the command's status when the trailing printf runs (the next prompt's precmd hooks would reset it). A timed-out exec must leave the session usable: interrupt + grace guarantee the trailing printf executes and the shell returns to a prompt for follow-up calls. Each exec renders through its own ephemeral renderer so concurrent execs are isolated and markers sit near the buffer bottom regardless of scrollback history.

**Probe:** `packages/server/tests/session-exec.test.ts` — :38 `echo hello-world` ⇒ exitCode 0, output contains hello-world; :52 `false` ⇒ exitCode 1; :60 `cd /tmp && pwd` then bare `pwd` ⇒ `/tmp` (proves state persists across execs in the shared shell); :110 `sleep 30` with 1000ms timeout ⇒ `timedOut===true && exitCode===null` (comment pins why 200ms raced unreliably and 1000ms was chosen).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "SessionCommandExecutor|buildExecResult", fields: ["lines"], limit: 10 });
```

## Verdict
Adopt the marker-token protocol (random token, start/end pair, `%d` exit suffix), single-line `;` chaining, raw-stream exit-code recovery, timeout-commit + interrupt-grace semantics, and render-through-fresh-headless-terminal extraction; adapt the token alphabet, size/time limits (16MB/30min/500ms are measured choices, not laws), and marker prefixes to your host; omit the one-shot transient-session route (`POST /exec`, `index.ts`:907+, spawns/kills its own PTY) unless you also want the stateless agent entry point. Coverage caveat: probes cite on-disk vite-plus integration tests (excluded from graph index by design); suite is tagged `integration` — needs a real PTY host to run.
