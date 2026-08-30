<!-- capsule-v2 -->
# boot-manifest-esm-bootstrap — how does a 190-feature extension boot deterministically when MV3 content scripts can't load ES modules?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** What runs before what at content-script startup, and which ordering constraints are load-bearing?

## Two-line ESM bootstrap
**Path/Symbol:** `source/content-script.ts` (whole file, :1–2).
**Signature:** none — side-effect module.
**Data Shape:** manifest-declared static script; dynamically imports the bundled ESM entry from extension assets.

### Decisive source
```ts
// Workaround to add ESM support to content scripts
void import(chrome.runtime.getURL('assets/refined-github.js'));
```

**Flow:** MV3 registers this tiny static file as the content script → it dynamic-imports the real ESM bundle by runtime URL → all module semantics (top-level await-free init, shared imports, tree-shaken deps) become available inside the page.
**Invariant:** the static shim must stay dependency-free; everything else loads through the one dynamic import. `void` marks deliberate fire-and-forget.
**Probe:** no direct test possible (browser registration contract); executed pin: `grep 'import\(chrome\.runtime\.getURL' source/content-script.ts` → line 2, and the file is exactly 2 lines (`wc -l` = 2).

## Ordered import manifest — import order IS run order
**Path/Symbol:** `source/refined-github.ts` (whole file, 221 lines): deduplicator-first :3, CSS-only block :9–25 (17 files), disableable CSS hybrids :31–35, JS features :38–221 (184 imports), hard-order comments :58 and :90.
### Decisive source
```ts
// Core feature that needs to run first; it serves the `deduplicate` key.
import './features/rgh-deduplicator.js';
…
import './features/last-update-sort.js'; // Must be after global-conversation-list-filters and conversation-links-on-repo-lists
…
import './features/actionable-pr-view-file.js'; // Must be before more-file-links
```
**Flow:** every feature module calls `feature-manager.add()` at its own import top level → ES module evaluation order (= manifest order) is therefore registration order AND readiness-promise insertion order → `globalReady` later runs inits in that sequence on each navigation.
**Invariant:** bare side-effect imports make ordering LOAD-BEARING: moving a feature line can break another feature silently. The first import must keep serving `deduplicate` before any caller-ID-mark consumer evaluates. New CSS belonging to a JS feature must be imported from the `.tsx`, not appended to the CSS-only block (:27–28 comment).
**Probe:** executed pins: `grep 'rgh-deduplicator|Must be after|Must be before' source/refined-github.ts` → lines 3, 58, 90; feature-import census `grep -c "^import './features/"` = 207 lines total (17 `.css` + 5 hybrid `.js` + 184 feature `.js` + deduplicator).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", qn_pattern: "refined-github\\.source\\.content-script\\..*" });
// total: 1 — File node only (no exported symbols): the file IS pure side effect
```
Executed 2026-08-26 @ pin 3187161.

## Verdict
Adopt the dynamic-import ESM bootstrap verbatim for any MV3 ESM extension, and adopt "manifest-as-ordered-registration" with explicit order comments + a first-run meta-feature slot. Adapt the bundler asset path (`assets/refined-github.js`) to your build layout. Omit GitHub's specific feature roster. Coverage caveat: no unit tests exist for either file — probes are byte-exact source pins; both paths `no_recorded_issue` @ gen 2026-08-24T14:04:43Z.
