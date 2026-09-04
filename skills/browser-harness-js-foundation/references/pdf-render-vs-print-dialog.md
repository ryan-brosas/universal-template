<!-- capsule-v2 -->
# pdf-render-vs-print-dialog — how do you get a PDF out of a page whose own button opens the OS print dialog?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** What does Page.printToPDF not render, and what are the two escapes when a site calls window.print()?

## Render + intercept ladder
**Path/Symbol:** `skills/cdp/interaction-skills/print-as-pdf.md` whole doc — direct render (:5–31), window.print interception (:33–53), print-friendly URL (:55–63), Traps (:65–70).
**Signature:** `Page.printToPDF({printBackground:true, paperWidth, paperHeight, preferCSSPageSize:true, pageRanges?, transferMode:'ReturnAsStream'?})`; interception: `window.print = () => { window.dispatchEvent(new Event('beforeprint')); window.__printed__ = true }` then printToPDF yourself.
**Data Shape:** printToPDF renders server-side in the Chrome process — works with NO dialog, undetectable by the page. CDP **cannot** interact with the OS print dialog. Escape A: intercept window.print (detectable via toString()); Escape B: find and navigate to the underlying print-friendly URL (e.g. `/invoice/123?print=1`) then printToPDF.

### Decisive source
```md
- **`printBackground: false` (default) skips background colors and images.**
  Invoices, receipts, and anything design-heavy look empty without it.
- **`Page.printToPDF` uses its own print-media CSS** (`@media print`). If the
  page hides elements with `display: none` under `@media print`, they'll be
  missing from your PDF. Override with `Emulation.setEmulatedMedia({ media:
  'screen' })` first.
```

**Flow:** want PDF → printToPDF(printBackground) → missing content? → either @media print hid it (setEmulatedMedia screen first) or fonts substituted → site's own Print button? → CDP can't drive the OS dialog → intercept or URL-salvage → very large docs use ReturnAsStream / pageRanges / smaller scale.
**Invariant:** The PDF renderer applies PRINT media emulation by default — what the viewport shows and what printToPDF captures are different documents unless you force media 'screen'. background-off default is a content-destroying footgun for styled pages.
**Probe:** `grep -cF 'printBackground: false' skills/cdp/interaction-skills/print-as-pdf.md` → 1; `grep -cF '@media print' <same>` → 1; `grep -cF 'setEmulatedMedia' <same>` → 1; `grep -cF '**cannot** interact with the OS print dialog' <same>` → 1; `grep -cF 'beforeprint' <same>` → 1; `grep -cF 'print=1' <same>` → 2.
**Retrieve:** search_code --project browser-harness-js --pattern "printToPDF" (Module node resolves line-exact).

## Verdict
Adopt printBackground-on + setEmulatedMedia-screen as defaults; adapt paper/margin/scale per doc class. Omit header/footer mustache templating if you never need printed metadata.
