<!-- capsule-v2 -->
# Icon / Implementation metadata family — how do tools, prompts, resources, and implementations carry display metadata?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6e3588efb46e7542d98498e5c630a0a86`; Codebase Memory `modelcontextprotocol`. **Question:** What is the shared name/title/icons display-metadata contract every registrable primitive and the Implementation handshake object inherits?

## BaseMetadata + Icons mixins and the title-precedence chain
**Path/Symbol:** `schema/draft/schema.ts` — `Icon` :890–927, `Icons` :934–947, `BaseMetadata` :954–969, `Implementation` :976–997; consumers: `Tool extends BaseMetadata, Icons` :1973 (`annotations.title` precedence note :2010), `Implementation` used as `_meta.clientInfo` value :90.
**Signature:** `interface Icon { src: string /* @format uri */; mimeType?: string; sizes?: string[]; theme?: "light"|"dark" }`; `interface Icons { icons?: Icon[] }`; `interface BaseMetadata { name: string; title?: string }`; `interface Implementation extends BaseMetadata, Icons { version: string; description?; websiteUrl? }`.
**Data Shape:** `Icon.src` = HTTP(S) URL or `data:` URI (Base64); `sizes` entries are `"WxH"` strings or `"any"` for scalable formats like SVG; absent `sizes` ⇒ usable at any size; absent `theme` ⇒ any theme.

### Decisive source
```ts
// schema/draft/schema.ts:956-968 — the name-vs-title contract:
//   name: Intended for programmatic or logical use, but used as a display name
//         in past specs or fallback (if title isn't present).
//   title: Intended for UI and end-user contexts — optimized to be
//          human-readable ... If not provided, the name should be used for
//          display (except for {@link Tool}, where `annotations.title`
//          should be given precedence over using `name`, if present).
// :938-944 — the rendering floor clients MUST/SHOULD support:
//   Clients that support rendering icons MUST support at least: image/png,
//   image/jpeg. SHOULD also support: image/svg+xml (security precautions),
//   image/webp.
```

**Flow:** every user-visible entity renders its identity by picking the first present of: entity `title` → `annotations.title` (tools only) → `name`; icons attach via the `Icons` mixin where supported; `Implementation` (name+title+version+description+websiteUrl+icons) self-identifies both sides in `server/discover` and per-request `clientInfo`.
**Invariant:** `name` is the stable programmatic identifier — never rename it for display reasons; UI copy belongs in `title`. Icon URLs are untrusted content: consumers SHOULD same-origin/trusted-domain check and treat SVG as active content (can embed scripts). `version` is REQUIRED on Implementation while everything beyond name/version is optional.
**Probe:** no runtime tests in the spec repo; machine anchors are the TS interfaces plus example JSONs under `schema/draft/examples/**` validated by `scripts/validate-examples.ts`, and `servers/src/everything/server/index.ts:46–51` shows a live Implementation literal (`name`, `title`, `version`). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "Icon Icons BaseMetadata Implementation websiteUrl title", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt BaseMetadata name/title split with the three-step display precedence, the Icon shape (uri/mimeType/sizes/theme), and the PNG/JPEG client floor; adapt icon hosting to your CDN (same-origin check stays); omit SVG/webp emission unless your consumers guarantee safe handling.
