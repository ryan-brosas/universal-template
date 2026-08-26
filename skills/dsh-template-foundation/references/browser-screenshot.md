<!-- capsule-v2 -->
# Browser screenshot — screenshot the active tab to a tmpdir PNG

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a CDP browser script capture a screenshot of the active tab to a uniquely named PNG in the OS tmpdir and print the path?

## Screenshot active tab
**Path/Symbol:** `.dsh/skills/pack-frontend/browser-tools/browser-screenshot.js` (whole file, 35 lines); the connect race (8–18), the last-tab guard (20–25), the timestamped filename (27–29), the screenshot (31).
**Signature:** `node browser-screenshot.js` → prints the PNG path; exits 1 if the browser is unreachable or no active tab. Uses `puppeteer-core` `connect({ browserURL: "http://localhost:9222" })`, `node:os` `tmpdir`, `node:path` `join`.
**Data Shape:** `timestamp = new Date().toISOString().replace(/[:.]/g, "-")`; `filename = screenshot-<timestamp>.png`; `filepath = join(tmpdir(), filename)`.

### Decisive source
```js
const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
const filename = `screenshot-${timestamp}.png`;
const filepath = join(tmpdir(), filename);
await p.screenshot({ path: filepath });
console.log(filepath);
await b.disconnect();
```

**Flow:** (1) connect under a 5s race; (2) take the last tab (guard if none); (3) build a timestamped filename (colons/dots replaced so the path is filesystem-safe); (4) `p.screenshot({ path: filepath })`; (5) print the path; (6) disconnect.

**Invariant:** the filename is unique per run (ISO timestamp) and filesystem-safe (no `:`/`.` in the filename); the screenshot is written to the OS tmpdir; the printed path is the exact written file.

**Probe:** no direct test file exists. Verified by direct source read (file indexed `no_recorded_issue` + `metadata_match`). The timestamped tmpdir write is the executable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "browser-screenshot screenshot tmpdir timestamp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the timestamped tmpdir screenshot + printed path. Adapt the output dir and filename prefix to the host. Omit if screenshots are not needed.
