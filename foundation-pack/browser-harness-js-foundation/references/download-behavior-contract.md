<!-- capsule-v2 -->
# download-behavior-contract — how are downloads routed to a chosen directory and confirmed complete?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** What makes Browser.setDownloadBehavior reliable, and when must a download go through the browser at all?

## Directory routing + completion signals
**Path/Symbol:** `skills/cdp/interaction-skills/downloads.md` whole doc — route-to-dir (:5–22), started-signal (:24–33), finished-signal (:35–44), plain-fetch shortcut (:48–61), click-triggered (:63–72), Traps (:74–80).
**Signature:** `Browser.setDownloadBehavior({behavior:'allow', downloadPath, eventsEnabled:true})` + `waitFor('Browser.downloadWillBegin', p => p.suggestedFilename.endsWith('.pdf'), 10_000)` + `waitFor('Browser.downloadProgress', p => p.state === 'completed', 60_000)`.
**Data Shape:** setDownloadBehavior is BROWSER-scoped (once per browser session). downloadPath must EXIST — "Chrome silently drops the file otherwise." Files arrive under suggestedFilename (rename after completion if needed). downloadProgress.state ∈ 'inProgress'|'completed'|'canceled'. Plain-HTTP GET without browser-added auth state → direct fetch is ~10× faster but LOSES cookie auth; copy cookies via Network.getCookies or use the browser path.

### Decisive source
```md
- **`downloadPath` must exist.** Chrome silently drops the file otherwise —
  always `mkdir -p` first.
...
- **If the "download" is actually just inline navigation** (PDF viewer opens
  in-page), there's no `downloadWillBegin` — you'll need `Page.printToPDF`
  or direct `fetch` instead.
```

**Flow:** mkdir -p → setDownloadBehavior(eventsEnabled) → trigger (link/click/navigation) → await downloadWillBegin (guid/suggestedFilename/url) → await downloadProgress completed → rename. Click-only triggers: pre-arm behavior THEN click THEN waitFor.
**Invariant:** The failure mode is SILENT (missing dir = no file, no error), so existence is precondition not cleanup; and absence of downloadWillBegin distinguishes true downloads from inline navigation — different salvage paths (printToPDF/fetch).
**Probe:** `grep -cF 'setDownloadBehavior' skills/cdp/interaction-skills/downloads.md` → 4; `grep -cF 'Chrome silently drops the file' <same>` → 1; `grep -cF 'suggestedFilename' <same>` → 2; `grep -cF "state === 'completed'" <same>` → 2; `grep -cF 'loses cookie-based auth' <same>` → 1; `grep -cF 'no \`downloadWillBegin\`' <same>` → 1.
**Retrieve:** search_graph --project browser-harness-js --query "setDownloadBehavior" resolves the generated.ts wrapper line-exact.

## Verdict
Adopt eventsEnabled + dual-signal (begin/completed) confirmation + the silent-drop precondition as the portable contract. Adapt the fetch-shortcut policy to your auth model. Omit nothing else in this doc.
