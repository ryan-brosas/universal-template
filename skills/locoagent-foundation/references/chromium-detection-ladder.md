<!-- capsule-v2 -->
# Chromium detection ladder — how do you pick "the user's browser" across 7 Chromium forks × 4 platform shapes without false positives?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When you must detect which installed Chromium browser to automate, what does each platform's existence check actually prove, and where are the forks' quirks encoded?

## chromium-detection-ladder
**Path/Symbol:** `src/utils/claudeInChrome/common.ts` (`CHROMIUM_BROWSERS` :39-216, `BROWSER_DETECTION_ORDER` :219-227, `detectAvailableBrowser` :345-409).
**Signature:** `detectAvailableBrowser(): Promise<ChromiumBrowser | null>` — first hit in fixed order wins, `null` = none found.
**Data Shape:** Per-browser config record keyed by `'chrome'|'brave'|'arc'|'chromium'|'edge'|'vivaldi'|'opera'`, each carrying `macos.appName`, per-platform `dataPath: string[]` segments, `linux.binaries: string[]`, `windows.registryKey`, optional `windows.useRoaming`. Order array: chrome → brave → arc → edge → chromium → vivaldi → opera ("most common first").

### Decisive source
```ts
case 'macos': {
  // Check if the .app bundle (a directory) exists
  const appPath = `/Applications/${config.macos.appName}.app`
  try {
    const stats = await stat(appPath)
    if (stats.isDirectory()) { return browserId }
  } catch (e) {
    if (!isFsInaccessible(e)) throw e   // ENOENT = keep walking; other errors propagate
  }
  break
}
```

**Flow:** iterate `BROWSER_DETECTION_ORDER` → per-platform probe: macOS stats `/Applications/<appName>.app` as a DIRECTORY (a stray file must not count); linux/wsl `which()` over ordered binary aliases (`google-chrome` before `-stable`); Windows stats the user-data dir under AppData/**Local**, except Opera which sets `useRoaming: true` → AppData/**Roaming**. Arc on Linux carries EMPTY arrays so it is skipped by the `length > 0` guards rather than by a special case.
**Invariant:** existence probes must distinguish "browser not installed" (ENOENT → continue) from real fs errors (`isFsInaccessible(e) || throw`) — swallowing all errors hides broken installs; and the Windows Local-vs-Roaming split lives in the DATA TABLE (`useRoaming` flag), never in control flow, so adding a fork cannot forget it.
**Probe:** no upstream test (tests/ = shell scripts). Deterministic pins: `grep -n "useRoaming" src/utils/claudeInChrome/common.ts src/utils/claudeInChrome/setupPortable.ts` → exactly the opera rows (:213, :89); `grep -n "binaries: \[\]" src/utils/claudeInChrome/common.ts` → arc-linux :112.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "detectAvailableBrowser BROWSER_DETECTION_ORDER", limit: 10 });
```

## Verdict
Adopt the data-table-plus-order-array shape and the per-platform probe semantics (directory-stat / which-alias-list / roaming-flag). Adapt the actual path tables to your fork set. Omit the specific extension IDs. Coverage caveat: probes are deterministic greps; upstream ships no unit tests for this file.
