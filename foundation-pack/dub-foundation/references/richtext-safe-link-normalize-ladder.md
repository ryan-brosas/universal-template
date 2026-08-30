<!-- capsule-v2 -->
# Link href normalize-then-verify ladder — how do I let users type "dub.co" while guaranteeing no unsafe scheme ever reaches the document?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What is the exact order of scheme normalization, safety verification, and error UX when saving a link?

## RichTextLinkModal save path
**Path/Symbol:** `packages/ui/src/rich-text-area/link-modal.tsx:normalizeLinkHref` (18–24) + `handleSave` (48–82); primitive at `packages/utils/src/functions/urls.ts:isSafeLinkHref` (20–32).
**Signature:** `normalizeLinkHref(value: string): string`; `isSafeLinkHref(href: string | null | undefined): href is string`.
**Data Shape:** accepts arbitrary user text; returns either an already-usable href (`http(s)://`, `mailto:`) or `https://` + trimmed input; empty string passes through unchanged; failure shape = toast error, modal stays open.

### Decisive source
```ts
export function isSafeLinkHref(href) {           // packages/utils/src/functions/urls.ts
  if (!href) return false;
  try {
    return SAFE_LINK_SCHEMES.has(new URL(href).protocol);  // {"http:", "https:", "mailto:"}
  } catch { return false; }
}
// link-modal.tsx
const finalHref = normalizeLinkHref(href);
if (!isSafeLinkHref(finalHref)) { toast.error("Enter a full URL starting with http://…"); return; }
```

**Flow:** onBlur normalizes the field (`https://` prefix when no usable scheme) → Save re-normalizes → `isSafeLinkHref` verifies via URL parse + protocol allowlist (javascript:/data: fail by construction) → on success chain focuses, replays `{from,to}` selection, then setLink or insertContent → close.
**Invariant:** normalize FIRST then verify the normalized value — verifying the raw input would reject `"dub.co"` and normalizing after verify would defeat the check (`javascript:alert(1)` fails `isSafeLinkHref` and is NOT prefixed because it already has a scheme-like head); the allowlist is parse-based (`new URL().protocol`) not regex, so malformed input falls to false rather than throwing.
**Probe:** `grep -c 'isSafeLinkHref' packages/ui/src/rich-text-area/link-modal.tsx` → **3** (normalize guard, verify guard, import); `grep -n 'mailto:' packages/ui/src/rich-text-area/link-modal.tsx` → lines 22 and 56.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "normalizeLinkHref RichTextLinkHoverTooltip", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "isSafeLinkHref SAFE_LINK_SCHEMES", limit: 5 });
```

## Verdict
Adopt the normalize→verify→toast funnel and the three-scheme allowlist verbatim (it is 13 lines); adapt the error copy and the `https://` default; omit nothing — this is a self-contained security primitive. Same guard reused by toolbar image-link prompt (rich-text-toolbar.tsx:192) and campaign image parse/render (campaign-editor-image.ts).
