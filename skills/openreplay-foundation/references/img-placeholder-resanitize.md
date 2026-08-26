<!-- capsule-v2 -->
# Image placeholder + resanitize hook — how are hidden/broken images replaced without breaking layout?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What per-image logic decides placeholder vs real src, and how does it participate in runtime re-sanitization?

## natural-size probe, sanitizer level, Firefox SVG carve-out
**Path/Symbol:** `tracker/tracker/src/main/modules/img.ts` — `sendImgAttrs` (:67–83), `sendPlaceholder` (:30–39), `resolveURL` (:6–20), `isSVGInFireFox` (:23–25), srcset resolution (:41–51), mutation observer on src/srcset (:84–103), `attachResanitizeCallback` (:120–124).
**Signature:** `sendImgAttrs(img: HTMLImageElement): void`; `isSVGInFireFox(url: string): boolean` (note: `.match(/.svg$|/i)` always truthy in FF — a latent bug to NOT copy).
**Data Shape:** PLACEHOLDER_SRC = static tracker placeholder jpeg; hidden/obscured ids get placeholder with recorded width/height attrs when missing.

### Decisive source
```ts
if (!img.complete) return
if (img.naturalHeight === 0 && img.naturalWidth === 0 && !isSVGInFireFox(img.src)) {
  sendImgError(img)                       // ResourceTiming event, not attribute
} else if (app.sanitizer.isHidden(id) || app.sanitizer.isObscured(id)) {
  sendPlaceholder(id, img)                // privacy placeholder keeps layout
} else { sendSrc(id, img); sendSrcset(id, img) }
```

**Flow:** bind → immediate attrs check → load/error listeners + src/srcset observer → on resanitize callback the SAME decision tree re-runs so toggling an ancestor's mask swaps real image ↔ placeholder live. Oversized src (>1e5 chars, data-URI spam) also degrades to placeholder.
**Invariant:** Broken images report ResourceTiming but keep their (broken) src — only privacy levels swap in the placeholder. The Firefox SVG check is buggy upstream; porters should implement "SVG ⇒ never error-placeholder" explicitly instead of copying the regex.
**Probe:** `grep -c 'static.openreplay.com/tracker/placeholder.jpeg' tracker/tracker/src/main/modules/img.ts` → `1`; `grep -c 'naturalHeight === 0 && img.naturalWidth === 0' tracker/tracker/src/main/modules/img.ts` → `1`; `grep -c 'attachResanitizeCallback' tracker/tracker/src/main/modules/img.ts` → `1`; direct test suite `tests/…` none for img module upstream (grep-pinned caveat).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "sendImgAttrs sendPlaceholder resolveURL img module", limit: 10 });
```

## Verdict
Adopt natural-size probe + sanitizer-level placeholder. Fix the SVG-in-Firefox regex. Omit srcset resolution if you don't capture responsive images.
