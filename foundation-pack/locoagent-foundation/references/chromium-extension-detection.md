<!-- capsule-v2 -->
# Extension detection scan — how do you find a browser extension on disk when the user may have any of 7 browsers and any number of profiles?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What directory grammar identifies an installed extension, and how does the portable variant differ from the app-internal one?

## chromium-extension-detection
**Path/Symbol:** `src/utils/claudeInChrome/setupPortable.ts` (`detectExtensionInstallationPortable` :147-213, `getAllBrowserDataPathsPortable` :97-135, `getExtensionIds` :14-18, duplicated tables :38-91).
**Signature:** `detectExtensionInstallationPortable(browserPaths, log?): Promise<{isInstalled: boolean, browser: ChromiumBrowser | null}>`; convenience `isChromeExtensionInstalled(log?)` self-supplies paths.
**Data Shape:** profile dirs = entries that are directories named exactly `'Default'` or matching `'Profile *'`; extension present = `<browserBase>/<profile>/Extensions/<extensionId>` readdir succeeds; IDs = `[PROD]` publicly, `[PROD, DEV, ANT]` when `USER_TYPE === 'ant'`.

### Decisive source
```ts
const profileDirs = browserProfileEntries
  .filter(entry => entry.isDirectory())
  .filter(
    entry => entry.name === 'Default' || entry.name.startsWith('Profile '),
  )
  .map(entry => entry.name)
```
and error polarity:
```ts
} catch (e) {
  // Browser not installed or path doesn't exist, continue to next browser
  if (isFsInaccessible(e)) continue
  throw e
}
```

**Flow:** enumerate browser base dirs in fixed order → readdir → filter to Chromium's profile-name grammar → for each profile × each extension ID try readdir of `Extensions/<id>` → first success returns `{isInstalled: true, browser}`; exhausting everything returns false. The file is a DELIBERATE DUPLICATE of common.ts tables ("Must match ... from common.ts" comments) because it must run with `process.platform` directly — usable from TUI AND VS Code extension hosts where the app's platform shim doesn't exist.
**Invariant:** ENOENT-class failures are SIGNALS here (browser absent / profile absent / extension absent all look alike), while other fs errors still propagate — same `isFsInaccessible` split as the detection ladder; and any new browser added to one table MUST be mirrored into the twin table (the comments are the only enforcement).
**Probe:** no upstream test. Deterministic pins: `grep -n "startsWith('Profile ')" src/utils/claudeInChrome/setupPortable.ts` → :178; `grep -n "Must match" src/utils/claudeInChrome/setupPortable.ts` → :20/:37/:54.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "detectExtensionInstallationPortable getAllBrowserDataPathsPortable", limit: 10 });
```

## Verdict
Adopt the profile/Extensions directory grammar and continue-on-missing semantics. Adapt the ID list and browser set. Omit the duplication if your host can share one module. Coverage caveat: no unit tests upstream.
