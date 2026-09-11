<!-- capsule-v2 -->
# Clipboard URL capture — how do you collect post URLs that exist nowhere in the DOM as links?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When a feed renders posts without anchor hrefs (LinkedIn search results), how does the executor obtain canonical per-post URLs without breaking on shifting element refs?

## Snapshot-driven UI-affordance capture with per-iteration re-resolution
**Path/Symbol:** `workflows/executors/linkedin-search-reply.ts`:`main` step 1 (:249-354); helpers `ab(cmd, timeout=30000)` (:126-138), `abEval(js, tmpDir)` (:140-158).
**Signature:** harvest regex over `ab('snapshot -i -c')` output; per-author loop calls `ab('scrollintoview @eN')`, `ab('click @eN')`, `ab('clipboard read')`.
**Data Shape:** Accessibility snapshot lines `button "Open control menu for post by <author>" [expanded=false, ref=eN]` and `menuitem "Copy link to post" [ref=eN]`; clipboard returns a URL string; dedup key is `url.split('?')[0]`.

### Decisive source
```ts
// NOTE: After each copy, the DOM changes (toast notification, refs shift).
// We must re-snapshot and find the control menu by author name each time.
for (const author of targetAuthors) {
  const freshSnap = ab('snapshot -i -c')
  const menuPattern = new RegExp(`button "Open control menu for post by ${author.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}" \\[expanded=false, ref=(e\\d+)\\]`)
  ...
  const copyMatch = menuSnap.match(/menuitem "Copy link to post" \[ref=(e\d+)\]/)
  if (!copyMatch) { ab('press Escape'); sleep(500); continue }
  ab(`click @${copyMatch[1]}`)
  const url = ab('clipboard read')
  if (url && url.startsWith('https://www.linkedin.com/')) {
    const cleanUrl = url.split('?')[0]!      // strip UTM params for cleaner dedup key
    postUrls.push({ url: cleanUrl, author })
  }
  // Dismiss toast: click button "Close" inside generic "Link copied…", else press Escape
}
```

**Flow:** harvest ALL control-menu `(author, ref)` pairs from one initial snapshot (:288-293) → slice to `maxPosts` → for EACH author: fresh snapshot → regex-find the menu by escaped AUTHOR NAME → scrollintoview + click → re-snapshot → click `Copy link to post` → `clipboard read` → validate `https://www.linkedin.com/` prefix → strip query → dismiss the "Link copied" toast (Close button, else Escape).
**Invariant:** Snapshot refs are SINGLE-USE — any click invalidates them, so identity (the author string, regex-escaped) is the only stable lookup key; every iteration re-resolves refs from a fresh snapshot. Clipboard content is untrusted input: prefix-validate before use, and dedup on origin+path only so UTM variants collapse. Menu-open failures MUST dismiss via Escape before continuing or the next iteration operates on a modal-covered page.
**Probe:** No direct test exists for this executor (coverage caveat — repo tests are `scripts/lib/*.test.ts` + `log-operation.test.ts` only). Deterministic probes: grep-pinned source comments :301-302 (ref-shift warning), :335 (clipboard prefix guard), :337 (UTM strip); `search_graph` resolves `loadCommented` :95-100 / `saveCommented` :102-106 backing the dedup set.
**Platform facts encoded in the header (:12-18), worth porting as-is:** LinkedIn post URLs are NOT DOM links; the compose modal lives in an iframe but comments do NOT; the comment box is `textbox "Text editor for creating comment"` (always visible on the detail page).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "clipboard read control menu copy link to post linkedin search", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the re-snapshot-per-action loop keyed on stable text identity, clipboard-prefix validation, UTM-stripped dedup keys, and mandatory modal dismissal. Adapt the snapshot grammar (`button "…" [ref=eN]`), the control-menu/copy-link labels, and the URL prefix to your target site. Omit nothing in the loop — skipping the Escape fallback or the toast dismissal deadlocks the next iteration. Coverage caveat: behavior claims are source-grounded, not test-run.
