<!-- capsule-v2 -->
# Tool-result summary views — normalize any result into {summary, expandedText, status}, then derive one-line outcomes from typed details

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How do you give every tool a compact, width-aware TUI line without each tool hand-rolling rendering — and make summaries carry OUTCOMES ("Saved · target: user · evicted: 2") rather than raw JSON?

## normalizeSharedOutputView + createSharedToolResultRenderer + memoryResultView
**Path/Symbol:** `src/tools/shared-output-view.ts:normalizeSharedOutputView` (:59–70), `sanitizeDisplayText` (:42–46), `compactSummary` (:93–106), `restoreBackground` (:83–91), `createSharedToolResultRenderer` (:147–170); `src/tools/tool-result-views.ts:resultData` (:10–24), `memoryResultView` (:40–80), `searchResultView` (:82–90), `skillResultView` (:92–105).
**Signature:** `createSharedToolResultRenderer(adapt?) → (result, options, theme, context?) → Component`; `SharedOutputView = { summary: string, expandedText: string, status: "success" | "failure" | "empty" }`.
**Data Shape:** input = tool result `{ content: [{type:"text",text}], details }`; `resultData` prefers the typed `details` object and falls back to parsing a single JSON text block.

### Decisive source
```ts
// Normalizer — ONE place decides status & fallbacks:
const failure = result?.isError === true || details?.success === false || details?.isError === true;
const status = failure ? "failure" : expandedText.trim() ? "success" : "empty";
const summary = failure ? (detailsReason || firstLine(expandedText) || "Error")
                        : (firstLine(expandedText) || detailsReason || "No output");

// Sanitizer — strip ANSI AND all control/surrogate/variant-selector chars,
// keeping only \n and \t:
stripAnsi(text).replace(/[\p{Cc}\p{Cs}\uFFF9-\uFFFB]/gu,
  (c) => (c === "\n" || c === "\t") ? c : "");

// Width-aware compaction — failures/warnings keep their TAIL (the reason lives there):
if (!preserveTail || width < 13) return truncateToWidth(summary, width, "…");
const tailWidth = Math.max(6, Math.floor(width / 2));
return `${sliceByColumn(summary, 0, headWidth, true)}…${sliceByColumn(summary, fullWidth - tailWidth, tailWidth, true)}`;

// Domain view — outcome classification from message REGEXES + counters:
const outcome = /^Entry added\.$/.test(primaryMessage) || /^Failure memory saved:/.test(primaryMessage) || evicted > 0 ? "Saved"
  : /^Entry replaced\.$/.test(primaryMessage) ? "Replaced"
  : /^Entry removed\.$/.test(primaryMessage) ? "Removed"
  : /^Entry already exists/.test(primaryMessage) ? "Unchanged" : "Updated";
parts.push(outcome);                       // → "Saved · target: project · category: convention · evicted: 1"
```

**Flow:** (1) every registration wraps its adapter via `createSharedToolResultRenderer(memoryResultView|searchResultView|skillResultView)`; (2) the normalizer sanitizes, classifies status, picks summary fallbacks; (3) the domain adapter overlays outcome vocabulary from typed details; (4) the renderer handles expansion (`expandedText` vs summary + key hint), partial-state prefixing ("In progress: "), per-status theming/background restoration, and hint-width budgeting.
**Invariant:** status is derived from THREE sources of truth (`isError`, `details.success`, `details.isError`) because tools fail through different channels; context `isError` OVERRIDES the adapted status at render time; failure summaries preserve tails because error reasons are suffix-positioned; sanitization happens BEFORE width math so invisible characters cannot desynchronize column layout.
**Probe:** `tests/tools/shared-output-view.test.ts` (status matrix, sanitizer, tail-preserving truncation, background restore) + `tests/tools/tool-result-renderer-wiring.test.ts` (each memory/session/skill tool registered with the shared renderer). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "normalizeSharedOutputView createSharedToolResultRenderer memoryResultView", limit: 5 })`

## Verdict
Adopt for any multi-tool agent UI. Adapt theme color names, key-hint API, and outcome regexes to your message catalog. The three-source status merge and tail-preserving failure truncation are the parts porters get wrong.
