<!-- capsule-v2 -->
# Multiline classification ladder — option overrides, intellisense forces multiline, single-line-comment veto, language useMultiline

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** Who decides whether a suggestion may span multiple lines, and in what precedence?

## Key facts
**Path/Symbol:** `core/autocomplete/classification/shouldCompleteMultiline.ts` (whole, 53L); sole call site `core/autocomplete/CompletionProvider.ts:230` (`!helper.options.transform || shouldCompleteMultiline(helper)` gates the stream-transform pipeline); language hooks in `constants/AutocompleteLanguageInfo.ts:39` (`useMultiline?:`) and Markdown impl :349-366.
**Signature:** `shouldCompleteMultiline(helper): boolean`; `language.useMultiline?.({prefix, suffix}): boolean | undefined` — undefined ⇒ default true.
**Data Shape:** decision inputs: `helper.options.multilineCompletions` ("always"|"never"|default), `helper.input.selectedCompletionInfo`, `helper.lang.singleLineComment`, last prefix line vs comment token, pruned prefix/suffix passed to the language hook.

### Decisive source
```ts
// :16-53 — the full ladder, verbatim order:
switch (helper.options.multilineCompletions) {     // 1. explicit user option
  case "always": return true;
  case "never":  return false;
}
if (helper.input.selectedCompletionInfo) return true; // 2. intellisense active ⇒ MUST multiline
// 3. mid-line check is COMMENTED OUT upstream (:31-34) — dead by choice
if (helper.lang.singleLineComment &&                 // 3. typing INSIDE a // comment
    helper.fullPrefix.split("\n").slice(-1)[0]?.trimStart()
      .startsWith(helper.lang.singleLineComment)) return false;
return shouldCompleteMultilineBasedOnLanguage(       // 4. language hook, default true
  helper.lang, helper.prunedPrefix, helper.prunedSuffix);
```
```ts
// Markdown :349-366 — the only stock useMultiline: block starters force single-line
const singleLineStarters = ["- ", "* ", /^\d+\. /, "> ", "```", /^#{1,6} /];
```

**Flow:** CompletionProvider asks once per request before attaching filters; "always"/"never" short-circuit everything; a selected intellisense item FORCES multiline true (the completion must wrap/replace the selection, which can span lines); a cursor sitting on a single-line comment vetoes multiline so suggestions can't spill out of the comment; otherwise the language decides (Markdown list/quote/heading/code-fence lines stay single-line).

**Invariant:** precedence is fixed and surprising in two places: intellisense BEATS the comment veto (selection handling outranks comment context), and the mid-line heuristic is deliberately disabled — reintroducing it changes behavior for every mid-line trigger. The language hook receives PRUNED prefix/suffix while the comment test reads the FULL prefix's last line — mixing those two inputs is a classic port bug.

**Probe:** `grep -c 'selectedCompletionInfo' core/autocomplete/classification/shouldCompleteMultiline.ts` → 1; `grep -c 'isMidlineCompletion' core/autocomplete/classification/shouldCompleteMultiline.ts` → 2 (definition :4 + commented call :32 — zero LIVE call sites); `grep -c 'multilineCompletions' core/autocomplete/classification/shouldCompleteMultiline.ts` → 1; `grep -c 'useMultiline' core/autocomplete/constants/AutocompleteLanguageInfo.ts` → 2 (:39 type decl, :349 Markdown impl).

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "shouldCompleteMultiline multilineCompletions useMultiline", limit: 8 })`

## Verdict
Adopt the four-rung ladder with its exact precedence and keep the mid-line rung disabled unless you consciously re-enable it. Extend per-language `useMultiline` hooks for your own block-starter grammars.
