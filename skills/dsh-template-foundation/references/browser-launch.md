<!-- capsule-v2 -->
# Browser launch — idempotent Chrome on :9222 with optional profile sync

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How starts a persistent, reusable Chrome instance on the CDP port `:9222` that is idempotent (reuse if already running) and optionally syncs the user's real Chrome profile (cookies/logins)?

## Idempotent CDP browser launch
**Path/Symbol:** `.dsh/skills/pack-frontend/browser-tools/browser-start.js` (whole file, 91 lines); `SCRAPING_DIR` (16), the connect-check (19–29), the profile rsync (42–57), the spawn (59–68), the readiness poll (71–89).
**Signature:** `node browser-start.js [--profile]` → exit 0 when Chrome is running on :9222, exit 1 if it never becomes reachable. Uses `puppeteer-core` `connect({ browserURL: "http://localhost:9222" })`.
**Data Shape:** `SCRAPING_DIR = ${HOME}/.cache/browser-tools`; `--profile` rsyncs `${HOME}/Library/Application Support/Google/Chrome/` into it (macOS path). Spawns `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` detached with `--remote-debugging-port=9222`, `--user-data-dir=${SCRAPING_DIR}`, `--no-first-run`, `--no-default-browser-check`.

### Decisive source
```js
const SCRAPING_DIR = `${process.env.HOME}/.cache/browser-tools`;

// Idempotent: if already running on :9222, reuse it.
try {
  const browser = await puppeteer.connect({ browserURL: "http://localhost:9222", defaultViewport: null });
  await browser.disconnect();
  console.log("✓ Chrome already running on :9222");
  process.exit(0);
} catch { /* not yet running */ }

// Clear stale singleton locks so Chrome can start cleanly.
execSync(`rm -f "${SCRAPING_DIR}/SingletonLock" "${SCRAPING_DIR}/SingletonSocket" "${SCRAPING_DIR}/SingletonCookie"`, { stdio: "ignore" });

if (useProfile) {
  execSync(`rsync -a --delete \
    --exclude='SingletonLock' --exclude='SingletonSocket' --exclude='SingletonCookie' \
    --exclude='*/Sessions/*' --exclude='*/Current Session' --exclude='*/Current Tabs' \
    --exclude='*/Last Session' --exclude='*/Last Tabs' \
    "${process.env.HOME}/Library/Application Support/Google/Chrome/" "${SCRAPING_DIR}/"`, { stdio: "pipe" });
}

spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--remote-debugging-port=9222", `--user-data-dir=${SCRAPING_DIR}`, "--no-first-run", "--no-default-browser-check"],
  { detached: true, stdio: "ignore" }).unref();

// Poll up to 30x (500ms) until puppeteer can connect.
for (let i = 0; i < 30; i++) {
  try { const browser = await puppeteer.connect({ browserURL: "http://localhost:9222", defaultViewport: null });
        await browser.disconnect(); connected = true; break; }
  catch { await new Promise((r) => setTimeout(r, 500)); }
}
if (!connected) { console.error("✗ Failed to connect to Chrome"); process.exit(1); }
```

**Flow:** (1) try connecting to an existing :9222 browser — if present, disconnect and exit 0 (idempotent); (2) mkdir the scraping dir and clear stale singleton locks; (3) if `--profile`, rsync the real Chrome profile in (excluding session/lock files); (4) spawn Chrome detached on :9222 with the scraping user-data-dir; (5) poll up to 15s for a successful `puppeteer.connect`, exiting 1 on failure.

**Invariant:** only one Chrome instance is ever started (reuse if alive); the scraping profile dir is isolated from the user's real profile unless `--profile` is passed; stale singleton locks are cleared so Chrome starts; the launch is detached (survives the script exit).

**Probe:** no direct test file exists. Verified by direct source read (file indexed `no_recorded_issue` + `metadata_match`). The readiness poll and idempotent connect are the executable contract. Coverage caveat: macOS-specific Chrome path — adapt to the host.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "browser-start SCRAPING_DIR remote-debugging-port", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the idempotent connect-or-launch pattern, the singleton-lock clearing, the detached spawn, and the bounded readiness poll. Adapt the Chrome binary path, the profile source dir, and the user-data-dir to the host. Omit the `--profile` rsync if profile reuse is not needed.
