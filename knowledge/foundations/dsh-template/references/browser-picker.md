<!-- capsule-v2 -->
# Browser picker — inject `window.pick()` for interactive element selection

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a CDP browser script inject an interactive `window.pick(message)` helper into the page so the user can hover-highlight and click-select elements (Cmd/Ctrl-click to multi-select), returning element info with a CSS-parent selector path?

## Interactive element picker (`window.pick`)
**Path/Symbol:** `.dsh/skills/pack-frontend/browser-tools/browser-pick.js` (whole file, 163 lines); the injected `window.pick` (34–143), `buildElementInfo` (82–103), `onMove`/`onClick`/`onKey` (75–140), the result formatting (148–161).
**Signature:** `node browser-pick.js 'message'` → prints the selected element info (or array). Injects `window.pick` via `p.evaluate` and calls it with the message. Uses `puppeteer-core`.
**Data Shape:** `window.pick(message)` returns a Promise resolving to either a single `buildElementInfo` object (plain click) or an array of them (Cmd/Ctrl-click multi-select, or Enter). `buildElementInfo` returns `{ tag, id, class, text, html, parents }` where `parents` is a `tag#id.class > ...` chain up to `body`.

### Decisive source
```js
await p.evaluate(() => {
  if (!window.pick) {
    window.pick = async (message) => {
      return new Promise((resolve) => {
        const selections = []; const selectedElements = new Set();
        const overlay = document.createElement("div");
        overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;z-index:2147483647;pointer-events:none";
        const highlight = document.createElement("div");
        highlight.style.cssText = "position:absolute;border:2px solid #3b82f6;background:rgba(59,130,246,0.1);transition:all 0.1s";
        overlay.appendChild(highlight);
        const banner = document.createElement("div");
        banner.style.cssText = "position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#1f2937;color:white;padding:12px 24px;border-radius:8px;font:14px sans-serif;box-shadow:0 4px 12px rgba(0,0,0,0.3);pointer-events:auto;z-index:2147483647";
        document.body.append(banner, overlay);

        const cleanup = () => {
          document.removeEventListener("mousemove", onMove, true);
          document.removeEventListener("click", onClick, true);
          document.removeEventListener("keydown", onKey, true);
          overlay.remove(); banner.remove();
          selectedElements.forEach((el) => { el.style.outline = ""; });
        };

        const onMove = (e) => {
          const el = document.elementFromPoint(e.clientX, e.clientY);
          if (!el || overlay.contains(el) || banner.contains(el)) return;
          const r = el.getBoundingClientRect();
          highlight.style.cssText = `position:absolute;border:2px solid #3b82f6;background:rgba(59,130,246,0.1);top:${r.top}px;left:${r.left}px;width:${r.width}px;height:${r.height}px`;
        };

        const buildElementInfo = (el) => {
          const parents = []; let current = el.parentElement;
          while (current && current !== document.body) {
            const parentInfo = current.tagName.toLowerCase();
            const id = current.id ? `#${current.id}` : "";
            const cls = current.className ? `.${current.className.trim().split(/\s+/).join(".")}` : "";
            parents.push(parentInfo + id + cls); current = current.parentElement;
          }
          return { tag: el.tagName.toLowerCase(), id: el.id || null, class: el.className || null,
                   text: el.textContent?.trim().slice(0, 200) || null, html: el.outerHTML.slice(0, 500),
                   parents: parents.join(" > ") };
        };

        const onClick = (e) => {
          if (banner.contains(e.target)) return;
          e.preventDefault(); e.stopPropagation();
          const el = document.elementFromPoint(e.clientX, e.clientY);
          if (!el || overlay.contains(el) || banner.contains(el)) return;
          if (e.metaKey || e.ctrlKey) {
            if (!selectedElements.has(el)) { selectedElements.add(el); el.style.outline = "3px solid #10b981";
              selections.push(buildElementInfo(el)); updateBanner(); }
          } else { cleanup(); resolve(selections.length > 0 ? selections : buildElementInfo(el)); }
        };

        const onKey = (e) => {
          if (e.key === "Escape") { e.preventDefault(); cleanup(); resolve(null); }
          else if (e.key === "Enter" && selections.length > 0) { e.preventDefault(); cleanup(); resolve(selections); }
        };
        document.addEventListener("mousemove", onMove, true);
        document.addEventListener("click", onClick, true);
        document.addEventListener("keydown", onKey, true);
      });
    };
  }
});
const result = await p.evaluate((msg) => window.pick(msg), message);
```

**Flow:** (1) inject `window.pick` if absent; (2) build a pointer-events-none overlay + a moving highlight + a bottom banner; (3) on mousemove, highlight the element under the cursor; (4) on click, if Cmd/Ctrl add to the selection (green outline), else resolve with the selection (or the single element); (5) Escape resolves null, Enter resolves the multi-selection; (6) cleanup removes listeners/overlay/banner and clears outlines; (7) the Node script formats the resolved info.

**Invariant:** the overlay is `pointer-events:none` so it never intercepts clicks (except the banner, which is `pointer-events:auto`); the picker is idempotent (`if (!window.pick)`); Escape cancels to null; multi-select requires Cmd/Ctrl; the returned `parents` chain is a stable CSS-ish selector path.

**Probe:** no direct test file exists. Verified by direct source read (file indexed `no_recorded_issue` + `metadata_match`; functions `buildElementInfo`/`cleanup`/`updateBanner`/`onMove` resolve in the graph). The overlay/banner/selection contract is the executable behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "browser-pick buildElementInfo window.pick overlay", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the injected `window.pick` overlay/highlight/banner pattern, the Cmd/Ctrl multi-select, the Escape-cancel/Enter-confirm keys, and the `parents` CSS-chain selector. Adapt the highlight/banner colors and the 200/500-char truncation to the host. Omit if headless selection is preferred.
