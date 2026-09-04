<!-- capsule-v2 -->
# Edit-failure taxonomy — classifying why an edit-tool call failed into actionable categories

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When an agent's edit call errors, how do you classify the failure from its error text and payload so aggregate reports reveal WHAT KIND of edit-language failure dominates — and how do op-shape telemetry get counted?

## Regex ladder over error text + payload-shape fallback + canonical op-shape counting
**Path/Symbol:** `packages/metaharness/adapters/edit/runner.ts` — `EDIT_FAILURE_CATEGORIES`+`categorizeEditFailure` (223-256), `countHashlineOps`/`hashlineOpLabel` (289-348), warning extraction `extractHashlineWarnings`/`hasHashlineAutocorrectWarning` (1508-1523), raw-block capture (1535-1554).
**Signature:** `categorizeEditFailure(error: string, args: unknown): EditFailureCategory` over `"range-continuation" | "unified-diff" | "no-change" | "hash-mismatch" | "other"`; `countHashlineOps(args): Record<string, number> | null`.
**Data Shape:** failures recorded per toolCallId with `{args, error, rawBlock?, category?}`; hashline subtypes keyed by CANONICAL header shape (`PUT N.=N`, `PUT N.=M`, `CUT N*`, `PUT >N @reg`, …) derived by tokenizing the patch input, not string-matching.

### Decisive source
```ts
function categorizeEditFailure(error: string, args: unknown): EditFailureCategory {
    const payload = getEditPayloadFromArgs(args);
    const hasRangeReplacePayload = /^[1-9]\d*[a-z]{2}\.\.[1-9]\d*[a-z]{2}[ \t]*=/m.test(payload);
    if (/\\TEXT.* (?:continuation|has been removed)|range[- ]replacement continuation|LidA\.\.LidB=FIRST_LINE/i.test(error))
        return "range-continuation";
    if (/unified-diff syntax|\+Lid[=|]|\+[1-9]\d*[a-z]{2}[=|]/i.test(error)) return "unified-diff";
    if (/No changes made|no changes being made|replacement is identical/i.test(error)) return "no-change";
    if (/hash mismatch|expected hash|stale/i.test(error)) return "hash-mismatch";
    // Payload-shape fallback: a well-formed range-replace payload that still
    // "cannot parse" is a continuation mistake, not garbage.
    if (hasRangeReplacePayload && /unrecognized op|cannot parse|Lines must start/i.test(error))
        return "range-continuation";
    return "other";
}
```

**Flow:** on a failed edit-tool end, extract the tool's error text (string content blocks first, JSON fallback), enrich "No changes made" errors with an against-original diff preview, then classify via the ordered regex ladder — most specific families first, generic parse errors LAST and only after checking whether the payload itself looks like a range-replace attempt → successes are scanned for `Warnings:` sections where an `Auto-corrected ` prefix marks an autocorrect (counted separately from clean successes) → every attempted edit's patch input is tokenized to count canonical op shapes; totals deliberately span ALL runs including failed attempts ("the mix shows what the model reaches for, not just what landed").
**Invariant:** classification order matters (a unified-diff-syntax message inside a range-replace payload must classify as unified-diff, not the payload fallback); autocorrects are successes-with-asterisk, never failures; op-shape counts are computed at execution time from args and aggregated across all attempts — best-run-only aggregation would hide exactly the flailing the taxonomy exists to expose.
**Probe:** `packages/metaharness/adapters/edit/runner.test.ts:147-180` — `summarizes edit failure categories including range-continuation` pins the category table row (`| range-continuation | 1 | 100.0% |`) and the per-attempt report block (`- Category: range-continuation`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "categorizeEditFailure EDIT_FAILURE_CATEGORIES countHashlineOps hashlineOpLabel Auto-corrected", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any eval of structured-output tools: fixed category enum, ordered specificity ladder with a payload-shape final disambiguator, separate autocorrect accounting, and attempted-not-only-successful op telemetry. Adapt the regex families to your tool's real error strings (mine them from logs first) and the canonical shapes to your grammar. Category rollups directly test-pinned.
