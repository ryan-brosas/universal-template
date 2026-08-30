<!-- capsule-v2 -->
# Throttled auto-update — how does an extension self-update from npm without becoming a startup network hazard or a command-injection vector?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** What guards must wrap a fire-on-every-LLM-call update check?

## Throttle file + in-flight flag + strict-semver allowlist + execFile array args
**Path/Symbol:** `src/update.ts`: `checkForUpdate` (:114-178), `autoInstallLatest` (:89-112), `findNpmRoot` (:68-76).
**Signature:** `checkForUpdate(autoUpdate: boolean, notify?) -> Promise<void>`; `CHECK_INTERVAL_MS = 3 * 60 * 1000`; throttle stamp at `~/.<CONFIG_DIR>/agent/.billion-context-pi-update-check`.
**Data Shape:** registry fetch `registry.npmjs.org/<pkg>/latest` with 5s AbortSignal timeout; install = `npm install <pkg>@<version> --silent --no-audit --no-fund` in the located package root.

### Decisive source
```ts
// :89-93 — two independent defenses against a poisoned/MITM registry:
// "only accept a strict semver, then pass args as an array to execFile (never
//  via a shell string) so the version can never be interpreted as a command
//  even if it slipped through."
if (!SEMVER_RE.test(latest)) return false;   // ^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z-.]+)?$
execFile("npm", ["install", `${PACKAGE_NAME}@${latest}`, ...], {...})
```

```ts
// :17-19 + :128-129 — why the in-flight flag exists:
// "the context event fires on every LLM call, so several can race past the
//  throttle read before any writes the timestamp."
let updateInFlight = false;
```

**Flow:** opt-out ladder (config `autoUpdate:false` OR env `ACP_AUTO_UPDATE` ∈ {0,false,no,off} case-insensitive) → in-flight guard → read throttle stamp, write NEW stamp BEFORE the network call (fail-closed against hammering) → fetch latest → compare semver component-wise → on newer: auto-install and notify "Restart Pi to finish" (install takes effect next process start) or fall back to a manual-command notice. Also fires from BOTH session_start and every context event — safe only because of throttle+flag.
**Invariant:** (1) version strings from the network are DATA until regex-validated; interpolation into a shell is the vulnerability. (2) The throttle timestamp is written before checking, so a crashed check still rate-limits. (3) Every failure path is silent-best-effort — an updater must never take the host down. (4) Installed updates apply on restart; the message says so explicitly.
**Probe:** `tests/update.test.ts:19-50`: no-op when disabled (:19), every opt-out env value (:24), whitespace-trimmed env match (:33), findNpmRoot nested discovery (:41), terminates without node_modules ancestor — no Windows infinite loop (:46).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "checkForUpdate autoInstallLatest findNpmRoot SEMVER_RE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all four guards (opt-out ladder, in-flight flag, pre-write throttle stamp, semver+execFile-array install). Adapt the registry/package identity. Omit nothing — each guard has a distinct documented failure it prevents.
