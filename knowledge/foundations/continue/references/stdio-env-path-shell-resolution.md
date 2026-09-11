<!-- capsule-v2 -->
# stdio env & PATH resolution — why do GUI-spawned MCP servers need PATH rebuilt from the user's login shell?

**Source:** continue Apache-2.0 `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When your host process (IDE extension, daemon) spawns child CLI servers, how do you give them the user's real environment instead of the GUI's stripped one?

## Whitelist commons → config env spread → PATH from process.env → login-shell PATH adopted only if different

**Path/Symbol:** `core/util/shellPath.ts` whole (30 lines; graph range `getEnvPathFromUserShell` :5–30); consumer `core/context/mcp/MCPConnection.constructStdioTransport:556–613` with `COMMONS_ENV_VARS` at :49 and import at :33.
**Signature:** `getEnvPathFromUserShell(remoteName?: string): Promise<string | undefined>`.
**Data Shape:** spawn env record assembled per-connect: `{...COMMONS_ENV_VARS(defined-only), ...options.env, PATH}` where PATH starts from `process.env.PATH` and MAY be replaced by the shell-resolved value.

### Decisive source
```ts
// shellPath.ts — the whole mechanism:
if (process.platform === "win32" && !isWindowsHostWithWslRemote) return undefined;
if (!process.env.SHELL) return undefined;
const command = `${process.env.SHELL} -l -c 'for f in ~/.zprofile ~/.zshrc ~/.bash_profile ~/.bashrc; \
do [ -f "$f" ] && source "$f" 2>/dev/null; done; echo $PATH'`;
const { stdout } = await execAsync(command, { encoding: "utf8" });
return stdout.trim();            // catch ⇒ return process.env.PATH  (fallback)
```

**Flow:** `constructStdioTransport` builds the child env: COMMONS_ENV_VARS whitelist (`HOME, USER, USERPROFILE, LOGNAME, USERNAME`, defined-only) → server-configured `options.env` spread (config wins) → `PATH` seeded from `process.env.PATH`; then, on non-Windows OR win32-host-with-WSL-remote, calls `getEnvPathFromUserShell(ideInfo.remoteName)` and adopts the result ONLY when it differs from `process.env.PATH` (:583); any error is console.error'd and the seeded PATH stands. The reason this exists: GUI extension hosts are launched with minimal environments — `npx`/`uv`/version-manager shims installed via rc-files are invisible to `process.env.PATH`, so stdio servers fail with ENOENT even though the terminal finds them. Sourcing the four common profile files through a LOGIN shell reproduces the terminal's PATH. Windows-non-WSL returns undefined immediately (no `$SHELL` contract); WSL remotes DO resolve because the commands run inside Linux.
**Invariant:** the shell probe can only ever REPLACE PATH with a superset-ish variant and only when it actually differs — it never throws upward; every other variable comes from a fixed whitelist plus explicit config, so the child env stays deterministic apart from PATH.
**Probe:** no dedicated suite for shellPath.ts (recorded block: core/util glob enumerates 22 test files, none for it). Boundary evidence: `MCPConnection.vitest.ts:12–16` MOCKS `../../util/shellPath` to a constant `/usr/local/bin:/usr/bin:/bin` — pinning that the transport test isolates this seam. Graph caveat: inbound trace returns `callers_total: 0` (import-edge gap; real consumer verified by direct read of import :33 / call :580).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "getEnvPathFromUserShell user shell PATH login environment", limit: 8 });
```

## Verdict
Adopt whitelist-plus-PATH env construction and the login-shell PATH probe with differ-only adoption; adapt the profile-file list to your target shells; omit entirely if children run under a full session environment. Trap: sourcing rc-files executes arbitrary user shell code at CONNECT time — acceptable for a local dev tool, but gate it behind an explicit opt-in in multi-tenant hosts.
