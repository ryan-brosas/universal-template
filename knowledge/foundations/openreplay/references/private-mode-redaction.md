<!-- capsule-v2 -->
# privateMode global redaction — what does "mask everything by default" actually rewrite, field by field?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** Which surfaces does `privateMode` blank out, and which escape hatches (`data-openreplay-unmask`) survive?

## Every text-ish payload gets the `replaceAll(/./g, '*')` treatment
**Path/Symbol:** `tracker/tracker/src/main/modules/input.ts:230–232` (labels), `observer.ts:447–449` (alt/placeholder attrs), `modules/network.ts:104–108 & :146` (bodies + URL), `modules/console.ts:113–115` (console output), `modules/viewport.ts:52–57` (title/url/referrer), gate in `sanitizer.computeLevel:70–77`.
**Signature:** Option flag `privateMode?: boolean` on the Sanitizer; read as `app.sanitizer.privateMode`.
**Data Shape:** Boolean; when true every textual capture is replaced with equal-length `*` strings (or dropped entirely for network bodies).

### Decisive source
```ts
// network.ts — bodies deleted, not starred:
if (!options.capturePayload || app.sanitizer.privateMode) {
  delete reqResInfo.request.body
  delete reqResInfo.response.body
}
...
const url = app.sanitizer.privateMode ? '************' : message.url
```
```ts
// input.ts — click labels
if (app.sanitizer.privateMode) { label = label.replaceAll(/./g, '*') }
```

**Flow:** privateMode raises computeLevel to Obscured for any node lacking `data-openreplay-unmask` → text nodes wiped by stringWiper; labels/attrs/console/page-title masked via `replaceAll`; fetch/xhr bodies removed before send; URLs become fixed-length stars.
**Invariant:** The unmask attribute is the ONLY opt-out; it must be checked on the parent element for text nodes. Masking happens at capture time — nothing recoverable ships to the server.
**Probe:** `grep -cF 'delete reqResInfo.request.body' tracker/tracker/src/main/modules/network.ts` → `1`; `grep -c "label.replaceAll(/./g, '*')" tracker/tracker/src/main/modules/input.ts` → `1`; `grep -c 'privateMode' tracker/tracker/src/main/app/sanitizer.ts` → `5`.
**Coverage:** all cited files clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "privateMode computeLevel unmask delete reqResInfo", limit: 10 });
```

## Verdict
Adopt delete-not-star for bodies (stars of a JSON blob still leak length+structure). Adapt star length policy per surface. Omit the console proxy masking if your product doesn't record console.
