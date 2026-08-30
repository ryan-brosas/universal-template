<!-- capsule-v2 -->
# URL-open launchers — why does Windows open URLs through rundll32 and a quoted BROWSER env value, when every other platform execs directly?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you hand an arbitrary http(s) URL to the OS default browser without shell metacharacter injection or file:// misinterpretation?

## url-open-launchers
**Path/Symbol:** `src/utils/claudeInChrome/common.ts` (`openInChrome` :429-469) + `src/utils/browser.ts` (`openBrowser`, `validateUrl` :39-68, :3-18).
**Signature:** `openInChrome(url): Promise<boolean>` (detected Chromium); `openBrowser(url): Promise<boolean>` (system default + `BROWSER` env override).
**Data Shape:** input url string; output boolean success; both swallow-and-return-false on spawn errors (`browser.ts`) while `common.ts` lets non-ENOENT fs errors propagate during detection.

### Decisive source
```ts
case 'windows': {
  // Use rundll32 to avoid cmd.exe metacharacter issues with URLs containing & | > <
  const { code } = await execFileNoThrow('rundll32', ['url,OpenURL', url])
  return code === 0
}
```
and from `browser.ts`:
```ts
if (platform === 'win32') {
  if (browserEnv) {
    // browsers require shell, else they will treat this as a file:/// handle
    const { code } = await execFileNoThrow(browserEnv, [`"${url}"`])
    return code === 0
  }
```

**Flow:** `openBrowser` validates protocol FIRST (`http:`/`https:` only — `file:` or custom-scheme URLs are rejected before any process spawns), then resolves launcher per platform: win32 = `$BROWSER` (URL wrapped in literal quotes as argv element) else `rundll32 url,OpenURL <url>`; darwin = `open`; linux = `xdg-open`. `openInChrome` runs detection first, then macOS `open -a <appName> <url>`, linux tries each binary alias in order until exit 0.
**Invariant:** never route URLs through a shell on Windows — `rundll32 url,OpenURL` exists precisely because cmd.exe interprets `&`/`|`/`>` inside URLs; conversely a user-configured `BROWSER` command needs the URL AS A QUOTED ARG because browsers launched bare treat it as a file handle. Two opposite quoting rules for two different Windows paths — porting either one everywhere breaks the other.
**Probe:** no upstream test. Deterministic pins: `grep -n "rundll32" src/utils/claudeInChrome/common.ts src/utils/browser.ts` → common :452 (comment) / :453 (call) and browser :54; `grep -n "protocol !== 'http:'" src/utils/browser.ts` → :13.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "openBrowser openInChrome rundll32", limit: 10 });
```

## Verdict
Adopt the http/https-only pre-validation and the two distinct Windows launch strategies. Adapt binary names/appName tables. Omit the specific reconnect-page behavior of callers. Coverage caveat: no unit tests upstream; probes deterministic.
