<!-- capsule-v2 -->
# Browser navigation — navigate the active tab or open a new tab, with reload

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a CDP browser script navigate to a URL in the current (last) tab or a new tab, with an optional forced reload, behind a short connect timeout?

## Navigate active tab / new tab
**Path/Symbol:** `.dsh/skills/pack-frontend/browser-tools/browser-nav.js` (whole file, 45 lines); arg parsing (6–9), the connect race (20–30), the new-tab branch (32–35), the current-tab branch (36–43).
**Signature:** `node browser-nav.js <url> [--new] [--reload]` → exit 0 on success, 1 if the browser is unreachable or no URL given. Uses `puppeteer-core` `connect({ browserURL: "http://localhost:9222" })`.
**Data Shape:** `args = process.argv.slice(2)`; `newTab = args.includes("--new")`; `reload = args.includes("--reload")`; `url = args.find(a => !a.startsWith("--"))`. The active tab is `(await b.pages()).at(-1)`.

### Decisive source
```js
const b = await Promise.race([
  puppeteer.connect({ browserURL: "http://localhost:9222", defaultViewport: null }),
  new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 5000)),
]).catch((e) => {
  console.error("✗ Could not connect to browser:", e.message);
  console.error("  Run: browser-start.js");
  process.exit(1);
});

if (newTab) {
  const p = await b.newPage();
  await p.goto(url, { waitUntil: "domcontentloaded" });
  console.log("✓ Opened:", url);
} else {
  const p = (await b.pages()).at(-1);
  await p.goto(url, { waitUntil: "domcontentloaded" });
  if (reload) await p.reload({ waitUntil: "domcontentloaded" });
  console.log("✓ Navigated to:", url);
}
await b.disconnect();
```

**Flow:** (1) parse flags; (2) connect to :9222 under a 5s timeout (fail with a "Run browser-start.js" hint); (3) if `--new`, create a page and `goto`; else take the last page, `goto`, and `reload` if `--reload`; (4) disconnect. Uses `waitUntil: "domcontentloaded"` (not full load).

**Invariant:** connection is bounded by a 5s timeout so a dead browser fails fast with a clear message; navigation waits for DOMContentLoaded, not network idle; the active tab is always the last page in `b.pages()`.

**Probe:** no direct test file exists. Verified by direct source read (file indexed `no_recorded_issue` + `metadata_match`). The 5s connect race and last-tab selection are the executable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "browser-nav newTab reload pages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bounded-connect pattern (Promise.race with a 5s timeout), the last-tab selection, the `--new`/`--reload` flags, and `waitUntil: "domcontentloaded"`. Adapt the connect URL and wait strategy to the host. Omit the reload flag if not needed.
