<!-- capsule-v2 -->
# Headless-aware browser launch — how do you open one provider-issued HTTPS URL cross-platform without shell parsing, degrading honestly under headless linux?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** a background OAuth flow must hand its authorization URL to the OS browser safely (no shell interpolation), and on a displayless machine it must say so instead of silently spawning nothing.

## tui.openBrowser — boolean-outcome twin of bin.openBrowser
**Path/Symbol:** `src/tui.ts:115-135 openBrowser`; CLI twin `src/bin.ts:24-44 openBrowser` (owned as an invariant by `cli-auth-device-code.md`, whose decisive excerpt is added by this pass's refactor of that capsule).
**Signature:** tui: `(rawUrl: string) => boolean` — throws on non-HTTPS, returns `false` when headless, `true` after spawn; bin: `(rawUrl: string) => void` — throws on non-HTTPS, swallows synchronous spawn failure.
**Data Shape:** per-platform command table `{file, args}`: win32 → `rundll32.exe url.dll,FileProtocolHandler <href>`; darwin → `open <href>`; else → `xdg-open <href>`.

### Decisive source
```ts
/** Open one provider-issued HTTPS challenge without passing it through shell parsing. */
function openBrowser(rawUrl: string): boolean {
  const url = new URL(rawUrl)
  if (url.protocol !== 'https:') throw new Error(`refusing to open non-HTTPS authorization URL from ${url.host}`)
  if (process.platform === 'linux' && process.env.DISPLAY === undefined && process.env.WAYLAND_DISPLAY === undefined) {
    return false
  }
  const command = process.platform === 'win32'
    ? { file: 'rundll32.exe', args: ['url.dll,FileProtocolHandler', url.href] }
    : process.platform === 'darwin'
      ? { file: 'open', args: [url.href] }
      : { file: 'xdg-open', args: [url.href] }
  const child = spawn(command.file, command.args, {
    detached: true,
    stdio: 'ignore',
    windowsHide: true,
  })
  child.on('error', () => {})
  child.unref()
  return true
}
```

**Flow:** caller (`TuiLoginController.onEvent`) → strict URL parse → HTTPS-only gate → headless probe → platform command table → fire-and-forget spawn → boolean outcome decides the challenge text: `true` → "Opened the ChatGPT authorization page…", `false` → the raw URL embedded in "Open this ChatGPT authorization page: …" so the user can open it manually.
**Invariant:** the URL is passed as an argv element to a fixed executable — never through a shell string, so URL characters cannot inject commands; non-HTTPS authorization URLs are refused loudly with the offending host in the error; spawn is fully detached (`stdio:'ignore'`, `windowsHide`, `unref()`) and asynchronous spawn errors are swallowed because the printed/opened URL is always the manual fallback; the two twins differ deliberately — bin.ts returns void and wraps spawn in try/catch (CLI prints the URL anyway), while the tui variant probes `DISPLAY`/`WAYLAND_DISPLAY` on linux FIRST and returns `false` without spawning, converting "cannot open" into first-class data for the caller.
**Probe:** direct source read of both twins at :115-135 and :24-44; behavior boundary evidence from tests/tui.spec.ts (challenge text assertions live in the login flow, not this helper). Honest caveat: neither openBrowser variant has a dedicated unit spec (spawn is environment-dependent); the invariant chain is source-read evidence plus the shared HTTPS refusal line being byte-identical across both files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.(tui|bin)\\.openBrowser$', limit: 10 });
```
Executed live against project `dsh-codex`: total 2, has_more false (both twins returned; confirms they are distinct graph nodes, not merged closures).

## Verdict
Adopt argv-element spawning over shell strings, the loud non-HTTPS refusal, and returning launch success/failure as data instead of hiding it. Adapt the platform command table to your targets and the headlessness signals to your display servers. Omit retrying or queueing the open — the manual-fallback text is the recovery path. Coverage: src/tui.ts and src/bin.ts are `no_recorded_issue` + `metadata_match`.
