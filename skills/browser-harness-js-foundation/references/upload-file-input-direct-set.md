<!-- capsule-v2 -->
# upload-file-input-direct-set — why must file uploads never click, and what is the DataTransfer escape for input-less dropzones?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How do you attach local files reliably, including hidden inputs and react-dropzone surfaces?

## Direct file-input set + drop event synthesis
**Path/Symbol:** `skills/cdp/interaction-skills/uploads.md` whole doc — canonical path (:5–24), hidden inputs (:26–38), DnD zones (:40–61), verification (:63–65).
**Signature:** `DOM.getDocument({depth:-1})` → `DOM.querySelector('input[type="file"]')` → `DOM.setFileInputFiles({nodeId, files: ['/absolute/path']})`; dropzone fallback: in-page `DataTransfer` + `new File([blob], name, {type})` + dispatch dragenter/dragover/drop DragEvents.
**Data Shape:** paths must be ABSOLUTE; multiple files need the input's `multiple` attribute; fires `change` exactly like a real selection. Works regardless of visibility (display:none/opacity:0/off-screen) — find the INPUT, never click the styled button (OS file picker opens and CDP cannot dismiss it). `querySelector` returning `nodeId: 0` means the input hides inside a shadow root or iframe.

### Decisive source
```md
Sites commonly hide `<input type="file">` … `DOM.setFileInputFiles`
works **regardless of visibility** — find the input directly, don't click
the button:
```

**Flow:** locate input (even invisible) → setFileInputFiles → confirm via change listener or Network.requestWillBeSent upload POST — a screenshot often cannot show attachment success. No input at all? → synthesize the DOM drop with DataTransfer (detectable by antibot; prefer finding the accessibility-hidden input first).
**Invariant:** The OS file picker is modal to CDP — clicking any visible upload affordance risks an undismissable dialog; the direct set is both more reliable AND less detectable. Verification belongs on the network trace because visual state lags.
**Probe:** `grep -cF 'setFileInputFiles' skills/cdp/interaction-skills/uploads.md` → 2; `grep -cF '**absolute**' <same>` → 1; `grep -cF '`nodeId: 0`' <same>` → 1; `grep -cF 'new DataTransfer()' <same>` → 1; `grep -cF 'network trace' <same>` → 1.
**Retrieve:** search_graph --project browser-harness-js --query "setFileInputFiles" resolves the generated.ts wrapper line-exact.

## Verdict
Adopt direct-set as the only default path; adapt the DataTransfer recipe per dropzone framework. Omit the antibot caveat only at your peril — it is the documented tradeoff.
