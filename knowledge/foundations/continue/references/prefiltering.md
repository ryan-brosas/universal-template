<!-- capsule-v2 -->
# Prefiltering — cheap early bail-outs before any snippet gathering or LLM call

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** Before gathering snippets or calling the LLM, what cheap checks decide autocomplete should be skipped entirely for this keystroke?

## The prefilter gate
**Path/Symbol:** `core/autocomplete/prefiltering/index.ts:shouldPrefilter` (42–83).
**Signature:** `shouldPrefilter(helper: HelperVars, ide: IDE): Promise<boolean>`.
**Data Shape:** returns `true` to skip autocomplete for this keystroke; uses `helper.options`, `helper.filepath`, `helper.fileContents`, and the IDE's workspace dirs + continue-ignore arrays.

### Decisive source
```ts
export async function shouldPrefilter(helper, ide): Promise<boolean> {
  if (helper.options.disable) return true;                       // config.json disable
  if (helper.filepath === getConfigJsonPath()) return true;      // never autocomplete inside config.json
  const disableInFiles = [
    ...(helper.options.disableInFiles ?? []),
    "*.prompt",
    ...getGlobalContinueIgArray(),
    ...(await getWorkspaceContinueIgArray(ide)),
  ];
  if (await isDisabledForFile(helper.filepath, disableInFiles, ide)) return true; // ignore-pattern match
  if (helper.filepath.includes("Untitled") && helper.fileContents.trim() === "") return true; // no info
  return false;
}
```

**Flow:** four independent bail-outs: (1) the `disable` option, (2) being inside the continue `config.json` itself, (3) matching any disable pattern (user `disableInFiles` + `*.prompt` + global + workspace continue-ignore arrays) via the `ignore` library on the relative path, (4) an untitled file with empty contents. A language-specific end-of-line prefilter exists but is commented out.

**Invariant:** prefiltering is purely cheap and synchronous-ish (no snippet gathering, no LLM); the `ignore` library needs the RELATIVE path (`findUriInDirs`), not the absolute path; the continue-ignore arrays are merged from global + workspace sources.

**Probe:** no direct vitest for prefiltering (the logic is exercised through `CompletionProvider.provideInlineCompletionItems`). Coverage caveat: no direct test file — source-grounded; the config.json and `*.prompt` exclusions are the decisive behaviors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "shouldPrefilter isDisabledForFile", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four cheap bail-outs, the merged disable-pattern list, and the relative-path `ignore` matching; adapt the config.json path and continue-ignore sources to host; omit the commented language-specific prefilter. Coverage caveat: no direct test — source-grounded.
