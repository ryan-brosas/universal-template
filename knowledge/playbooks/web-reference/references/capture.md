# Capture: tool ladder and verified commands

Probe tool availability at capture time (`browser-harness-js --version`, `npx single-file --help`, `docker image inspect`); do not rely on versions frozen in this document. Commands here describe shape, not pinned releases.

## Tool ladder (cheapest sufficient)

| Need | Tool | Notes |
|---|---|---|
| Static page, source HTML only | `curl -fsSL <url> -o source.html` | no rendering; fine for server HTML |
| One page, faithful single-file copy | `npx single-file <url> page.html` | SingleFile CLI (AGPL-3.0, actively maintained); inlines CSS and assets |
| Rendered truth, any scripted page | `browser-harness-js` (CDP) | rendered DOM, computed styles, screenshots, viewport emulation |
| Whole-site raw archive | `browsertrix-crawler` (Docker) | WACZ archive; replay in ReplayWeb.page |
| Interaction flows | `cdp` skill recipes | clicks, hovers, dialogs via CDP |

Do not launch a site crawl for one hero. Do not start a browser when `curl` answers the question.

## Browser capture

Start a disposable headless browser and connect the harness to it:

```bash
chromium --headless=new --remote-debugging-port=9222 \
  --user-data-dir=/tmp/webref-profile --no-first-run --hide-scrollbars about:blank &
browser-harness-js 'await session.connect({wsUrl: await resolveWsUrl({port:9222})})'
browser-harness-js 'const t=await listPageTargets(); await session.use(t[0].targetId); t.length'
```

Plain `session.connect()` auto-detects the user's running profile browsers (Chrome, Chromium, Edge, Brave, Vivaldi, Opera are scanned). Use that path when the user's authorized session is required and the request makes that clear.

The browser sandbox stays on by default. Add `--no-sandbox` only when the runtime requires it (root in a container, known broken seccomp); it is an environment-specific exception, never the normal path.

Navigate and poll readiness. Single-expression snippets return values; multi-statement snippets need the heredoc form:

```bash
browser-harness-js 'await session.Page.navigate({url:"https://example.com/"})'
browser-harness-js '(await session.Runtime.evaluate({expression:"document.readyState",returnByValue:true})).result.value'
```

Rendered HTML (heredoc form; adapt paths to the bundle layout):

```bash
browser-harness-js <<'EOF'
const fs = await import("node:fs");
const r = await session.Runtime.evaluate({expression: "document.documentElement.outerHTML", returnByValue: true});
fs.writeFileSync("captures/2026-08-31/pages/home/rendered.html", r.result.value);
return fs.statSync("captures/2026-08-31/pages/home/rendered.html").size
EOF
```

Screenshots (output pixels are CSS pixels times deviceScaleFactor):

```bash
browser-harness-js <<'EOF'
const fs = await import("node:fs");
const r = await session.Page.captureScreenshot({format: "png"});
fs.writeFileSync("captures/2026-08-31/screenshots/home-desktop.png", Buffer.from(r.data, "base64"));
return fs.statSync("captures/2026-08-31/screenshots/home-desktop.png").size
EOF
```

Mobile viewport. The override persists across navigations; clear it before returning the browser to normal use:

```bash
browser-harness-js 'await session.Emulation.setDeviceMetricsOverride({width:390,height:844,deviceScaleFactor:2,mobile:true})'
browser-harness-js 'await session.Emulation.setTouchEmulationEnabled({enabled:true})'
browser-harness-js 'await session.Emulation.clearDeviceMetricsOverride()'
```

`Emulation.setUserAgentOverride` exists on the SDK when a mobile user agent string matters.

Extraction expressions for CSSOM, computed styles, and custom properties live in `references/extraction.md`.

## Modes

- **quick**: navigate, screenshot the region (`captureScreenshot` with `clip` or element box from `DOM.getBoxModel`), computed styles for the region, fonts and colors. No crawl.
- **page**: source HTML (`curl`), rendered HTML, CSSOM dump, custom properties, computed styles, desktop and mobile screenshots, asset list.
- **site**: bounded crawl (`references/scope.md`) over representative routes; per-page evidence plus a WACZ archive; screenshots at representative viewports.
- **deep**: site evidence plus tokens, typography, spacing, shadows, breakpoints, motion, patterns, interaction states. Earned by the request, not the default.
- **refresh**: capture into a new dated directory, then compare (`references/storage.md`).

## One-page fallback

```bash
npx single-file "https://example.com/page" page.html
```

SingleFile inlines styles and assets into one HTML file. Good for "use this one page" when a browser session is overhead. The AGPL license covers the tool, not the captured output stored as evidence.

## Site archive (WACZ)

```bash
docker run -v "$PWD/crawls:/crawls/" webrecorder/browsertrix-crawler:<pinned-version> crawl \
  --url https://example.com --generateWACZ --text --collection webref --limit 25
```

The crawl writes `crawls/collections/webref/webref.wacz`. A WACZ is a zip: `unzip -l site.wacz` lists it, and extraction yields HTML, CSS, JavaScript, images, and `pages.jsonl`. Replay uses ReplayWeb.page. Pin a published image version for repeatable captures; `--limit` bounds the page count; keep the crawl on one host, with the Browsertrix Crawler user guide for scope options. Large archives stay out of Git by default (`references/storage.md`).

## Authenticated pages

Use the user's running browser profile via `session.connect()` auto-detection only when the user asked for it and the target page is theirs to view. Never fill credentials into a capture script, never export cookies or storage into the bundle, and never store tokens in `manifest.json`. The validator rejects credential-like material.

## Interaction states

When the question needs hover, dropdown, modal, or mobile-menu evidence, drive the page with `cdp` skill recipes (`axClick`, `Input.*`), then capture rendered HTML plus a screenshot per state and name files by state. Non-destructive states only.
