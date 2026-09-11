<!-- capsule-v2 -->
# Snippet formatting + initial prefix/suffix — comment-marked context blocks, Path: headers, selected-completion splice

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How are gathered snippets and the raw prefix/suffix shaped into prompt-ready text (comment wrapping, path headers, clipboard handling, injected details, selection splicing)?

## Key facts
**Path/Symbol:** `core/autocomplete/templating/formatting.ts` (whole, 100L, `formatSnippets` :71-100); `constructPrefixSuffix.ts` (whole, 43L, `constructInitialPrefixSuffix`); consumer `templating/index.ts:178`; caller `util/HelperVars.ts:56`.
**Signature:** `formatSnippets(helper, snippets: AutocompleteSnippet[], workspaceDirs): string`; `constructInitialPrefixSuffix(input, fileContents) → {prefix, suffix}`.
**Data Shape:** four snippet kinds (`Code`, `Diff`, `Clipboard`, `Static`) from `snippets/types.ts`; every snippet becomes a comment-wrapped block; output ends with the CURRENT file's own `Path:` comment.

### Decisive source
```ts
// formatting.ts :16-23 — every line of every snippet is commented out:
const addCommentMarks = (text: string, helper: HelperVars) => {
  const commentMark = getCommentMark(helper);      // lang.singleLineComment
  return text.trim().split("\n")
    .map((line) => `${commentMark} ${line}`).join("\n");
};

// :29-36 — clipboard has no file: it masquerades as an Untitled code snippet
return formatCodeSnippet({ filepath: "file:///Untitled.txt",
                           content: snippet.content, type: AutocompleteSnippetType.Code },
                         workspaceDirs);

// :45 + :98 — Path headers use 2-part relative paths, and the current file's
// header comes LAST so the model knows where the cursor's file starts:
content: `Path: ${getLastNUriRelativePathParts(workspaceDirs, snippet.filepath, 2)}\n${snippet.content}`
... .join("\n") + `\n${currentFilepathComment}`;
```
```ts
// constructPrefixSuffix.ts :22-26 — intellisense SELECTION is spliced INTO the prefix:
let prefix = getRangeInString(fileContents, { start: {line:0,character:0},
  end: input.selectedCompletionInfo?.range.start ?? input.pos })
  + (input.selectedCompletionInfo?.text ?? "");
```

**Flow:** HelperVars builds initial prefix/suffix once per request (selection text appended after cutting at selection start; `injectDetails`, when set, is re-emitted as comment lines inserted BEFORE the cursor's own line) → gathered snippets flow through formatSnippets: kind-specific shaping (code gets Path header, diff/static pass through, clipboard becomes pseudo-file) → all are commentified line-by-line → joined newline-separated → current file's Path comment appended last.

**Invariant:** snippets are ALWAYS wrapped in comment syntax so they can never be mistaken for completable code — a porter who emits raw snippet bodies invites the model to continue them. The current file's Path header must be the final block (proximity-to-cursor signal). Selection splicing means the prefix already CONTAINS the selected identifier — downstream pruning operates on that combined string, so stripping the splice breaks intellisense-aware completions.

**Probe:** `grep -c 'addCommentMarks' core/autocomplete/templating/formatting.ts` → 3; `grep -cF 'file:///Untitled.txt' core/autocomplete/templating/formatting.ts` → 1; `grep -c 'selectedCompletionInfo?.text' core/autocomplete/templating/constructPrefixSuffix.ts` → 1; `grep -c 'injectDetails' core/autocomplete/templating/constructPrefixSuffix.ts` → 2.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "formatSnippets constructInitialPrefixSuffix addCommentMarks", limit: 8 })`

## Verdict
Adopt comment-wrapped, Path-headed snippet blocks with the current file last, and selection-spliced prefix construction. Adapt path-display depth (2 parts), comment token per language, and clipboard pseudo-filename to your host.
