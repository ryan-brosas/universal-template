<!-- capsule-v2 -->
# Native-host manifest install — why does Chrome force a wrapper script, and how do you register one host across every browser without failing on the browsers you don't have?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How is a native messaging host installed idempotently across 7 browsers, two OS manifest systems, and an argv-less `path` field?

## native-host-manifest-install
**Path/Symbol:** `src/utils/claudeInChrome/setup.ts` (`setupClaudeInChrome` :91-171, `createWrapperScript` :308-346, `installChromeNativeHostManifest` :191-266, `registerWindowsNativeHosts` :271-299, `NATIVE_HOST_IDENTIFIER` :36).
**Signature:** `createWrapperScript(command): Promise<string>` → `~/.claude/chrome/chrome-native-host` (sh, `exec <cmd>`) or `chrome-native-host.bat`; `installChromeNativeHostManifest(manifestBinaryPath): Promise<void>`.
**Data Shape:** manifest = `{name: 'com.anthropic.claude_code_browser_extension', path: <wrapper>, type:'stdio', allowed_origins: ['chrome-extension://<prodId>/', ...ant-only dev/ant ids]}`; Windows keeps ONE manifest under `%APPDATA%\Claude Code\ChromeNativeHost\` with per-browser `HKCU\...\NativeMessagingHosts\<name>` REG_SZ keys pointing at it.

### Decisive source
```ts
if (isNativeBuild) {
  // Create a wrapper script that calls the same binary with --chrome-native-host. This
  // is needed because the native host manifest "path" field cannot contain arguments.
  const execCommand = `"${process.execPath}" --chrome-native-host`
```
and write-skipping:
```ts
// Check if content matches to avoid unnecessary writes
const existingContent = await readFile(manifestPath, 'utf-8').catch(() => null)
if (existingContent === manifestContent) {
  continue
}
```

**Flow:** setup returns a DYNAMIC-scope stdio MCP config (`command: process.execPath, args:['--claude-in-chrome-mcp']`, native build vs cli.js path for source runs) + allowlisted tool names + system prompt; CONCURRENTLY fire-and-forget: create wrapper (skip write when byte-identical; chmod 0755) → write manifest into EVERY browser's NativeMessagingHosts dir (per-file failure logged, never fatal — "the browser might not be installed") → Windows: reg.exe add per browser key → if any manifest actually changed AND extension present, open the reconnect page so Chrome picks up the new host without reinstall.
**Invariant:** the wrapper exists because Chrome's manifest `path` cannot carry arguments — pointing it at the binary directly would launch the CLI WITHOUT the `--chrome-native-host` mode; installs are per-dir best-effort (partial success valid); reconnect-page side effect fires only on real content change (`anyManifestUpdated`), making reruns side-effect-free.
**Probe:** no upstream test. Deterministic pins: `grep -n "cannot contain arguments" src/utils/claudeInChrome/setup.ts` → :109/:303-304 (two independent comments); `grep -n "anyManifestUpdated" src/utils/claudeInChrome/setup.ts` → :216/:252. (Verified: :252 is the `if` site.)
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "installChromeNativeHostManifest createWrapperScript", limit: 10 });
```

## Verdict
Adopt wrapper-script indirection + content-equal skip + best-effort fan-out + change-gated reconnect. Adapt identifiers/paths to your product. Omit ant-only origin IDs. Coverage caveat: no unit tests upstream.
