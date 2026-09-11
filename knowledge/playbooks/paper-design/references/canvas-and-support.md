# Canvas, SVG, Snapshot, and support

Sources: [SVG](https://paper.design/docs/svg),
[Support](https://paper.design/docs/support),
[Local Snapshot images](https://paper.design/docs/support/snapshot-local-images),
[Snapshot quick start](https://paper.design/snapshot-extension).
Reviewed 2026-09-06. Use the visible app menu for platform/version-specific shortcuts.

## SVG editing

Paste source SVG into Paper to edit its vector layers. Move/resize/rotate layers;
change fills, strokes, and thickness. Enter path editing by double-clicking a path
or pressing Enter. Pen (`P`) edits/draws segments; Move (`M` in the vector guide)
adjusts control points and segments. Escape or double-click empty space exits.
Clicking with Pen inside an SVG creates a path there; outside creates a containing
SVG. Pixel snapping snaps path points to half-pixels; toggle it in the zoom menu
or Shift+Cmd+'. General canvas Move is documented as `V`, so distinguish contexts.

Create SVG (Shift+Cmd+J) opens AI generation and can use a selected frame as context.
Generation is for an explicit generation request, not a replacement for a real
Figma asset. For exact transfer use the actual vectors/images.

The vector page's roadmap includes improved guides/snapping, crop/scale/resize SVG
workflows, convert shapes to paths, and booleans; longer-term ideas include mirroring,
repeating, vector networks, anchoring, Anneal Brush, and Shape Builder. Do not promise
these from roadmap text. The page also documents existing layer transforms and Pen
creation; distinguish current layer/path operations from broader planned tooling.

## Snapshot: browser UI → editable Paper layers

Install/pin the browser extension only when needed and authorized. Activate via its
icon (documented shortcut Shift+Cmd+P), target an element, use Up/Down to refine the
selection, then click or Enter to capture. Paste into the intended Paper Desktop or
Web file. Customize activation at `chrome://extensions/shortcuts`.

May's [build log](https://paper.design/build-log#may-2026) announces Cmd+Enter for
full-page capture and OpenType-feature preservation. Verify important font features
in the actual result. Capture the relevant component first; a browser snapshot does
not retain application component identity, event handlers, or guaranteed token links.

### Local images / CORS

Paper must fetch image assets from the development server. Permit the exact origin
`https://app.paper.design` on the asset-serving routes, scoped to development. Keep
authentication and production policy intact; no wildcard-CORS or global browser
security workaround. Test the actual image URL and response headers, not only HTML.

The official guide covers every following framework:

| Framework | Configuration boundary |
|---|---|
| Astro | `security.allowedDomains` host check (5.14+) **and** Vite `server.cors` |
| Django | `django-cors-headers`, middleware, `CORS_ALLOWED_ORIGINS` |
| Express | `cors` middleware with exact origin |
| Fastify | `@fastify/cors` plugin with exact origin |
| Flask | `flask-cors` with exact origin |
| Next.js | `headers()` on required routes: allow origin, GET/OPTIONS, `Vary: Origin` |
| Nuxt | Vite CORS plus relevant `routeRules` headers |
| Rails | `rack-cors`, exact origin, GET/OPTIONS resources |
| Vite / Remix / SvelteKit | `server.cors.origin` |
| Webpack | `devServer.headers` |

Read the live framework snippet before editing its configuration. Minimal Vite
example (merge into existing config; do not overwrite plugins):

```js
server: {
  cors: { origin: 'https://app.paper.design' }
}
```

For Vite 6+ `/@fs/` cross-origin subresource failures, the docs mention both moving
assets to `public/` and stripping `Sec-Fetch-*` headers via a plugin. Prefer a
public development asset route; do not weaken fetch-metadata checks as a default.
Only expose the dev server to other machines when required and authorized.

## Shortcut map

The support page is the complete shortcut reference. High-value groups:

| Task | Documented macOS shortcuts |
|---|---|
| Create / structure | F frame, Shift+F wrap frame, Shift+A flex, Option+Shift+A remove flex, T text, R rectangle |
| Select hierarchy | Cmd+click deep select, Enter children/edit, Esc parent/clear, Tab/Shift+Tab siblings |
| Visibility / labels | Shift+Cmd+H hide, Shift+Cmd+L lock, Cmd+R rename, Option+L collapse tree |
| Order / geometry | `[`/`]` back/front, Cmd+`[`/`]` one step; arrows nudge, Shift larger nudge, Cmd+arrows resize |
| Align / distribute | Option+W/S/A/D top/bottom/left/right; Option+V/H centers; Control+Option+H/V distribute |
| Copy / replace | Cmd+C/V, Shift+Cmd+V paste on top, Shift+Cmd+R paste to replace, Cmd+D duplicate |
| Copy styles | Option+Cmd+C / Option+Cmd+V |
| Handoff | Option+T copy Tailwind, Option+R copy React CSS, Shift+Cmd+C copy PNG, Shift+Cmd+E export images |
| View | Cmd+0 actual size, Shift+1 fit all, Shift+2 fit selection; Space pan, Cmd+. hide/show UI |
| Measurement aids | Hold Option for distances; Cmd+' pixel grid; Shift+G layout guides |

Support also covers typography adjustments, opacity, clipping/fit/fill, image/SVG
creation, export video (paid plans), new windows/dashboard, and collaboration cursors.
Use the source for uncommon shortcuts rather than expanding this into a second
keybinding manual. Several shortcuts are context-sensitive; menu labels win.

## Troubleshooting routes

- **No MCP connection:** open a file in Paper Desktop; inspect host/server state.
  Stale sessions may need a restart. See `mcp-and-handoff.md`.
- **Changes invisible:** verify file/page identity with `get_basic_info`; background
  tabs can be mutation targets. A returned node ID is not proof of the intended page.
- **Corporate network / sign-in:** the docs recommend allowlisting `*.paper.design`.
  macOS proxy bypass uses `.paper.design` in network proxy settings. Ask the network
  owner for approval; do not change machine-wide policy automatically.
- **`paper://` links fail on Linux:** an AppImage may lack desktop/protocol-handler
  integration. The docs list Gear Lever, AppImageLauncher, or AppMan integration.
  Verify the installed package method before proposing a change.
- **WSL localhost cannot reach MCP:** the docs suggest WSL networking mode `mirrored`,
  followed by WSL restart. This affects running processes; coordinate before changing.
- **Images missing:** distinguish Figma extension authorization/rate limits from
  Snapshot CORS, unreachable asset URLs, and font/render problems. Diagnose the
  specific transfer path rather than reconnecting every integration.
