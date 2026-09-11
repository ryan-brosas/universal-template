<!-- capsule-v2 -->
# Library stack capture — how does the client know which user call triggered this API activity?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** How do I derive a clean apiName ("page.click") and a user-only stack from inside a deep internal call chain, without shipping library frames to users?

## Deepest library→user transition is the API entry
**Path/Symbol:** `packages/playwright-core/src/client/clientStackTrace.ts:captureLibraryStackTrace` (21-72) + helpers from `packages/utils/stackTrace.ts` (`captureRawStack`, `coreDir`, `parseStackFrame`, `filterStackFile`).
**Signature:** `captureLibraryStackTrace(): { frames: StackFrame[], apiName: string }`; StackFrame `{ file, line, column, function? }`.
**Data Shape:** raw V8 stack lines parsed to frames; each tagged `isPlaywrightLibrary = frame.file.startsWith(coreDir())`.

### Decisive source
```ts
// Deepest transition between non-client code calling into client
// code is the api entry.
for (let i = 0; i < parsedFrames.length - 1; i++) {
  const parsedFrame = parsedFrames[i];
  if (parsedFrame.isPlaywrightLibrary && !parsedFrames[i + 1].isPlaywrightLibrary) {
    apiName = apiName || normalizeAPIName(parsedFrame.frame.function);
    break;
  }
}

function normalizeAPIName(name?: string): string {
    if (!name)
      return '';
    // (\d) is to tolerate bundler renames Locator2 instead of Locator.
    const match = name.match(/(API|JS|CDP|[A-Z])([^\d]+)\d?\.(.*)/);
    if (!match)
      return name;
    return match[1].toLowerCase() + match[2] + '.' + match[3];
}
```

**Flow:** capture the RAW stack (Error.prepareStackTrace bypass, not `new Error().stack`, so getters can't interfere), parse every line, tag frames as library-or-user by file prefix, then scan from the innermost frame outward for the FIRST pair where the inner frame is library and the next outer is user code — that function name (e.g. `Page.click`) becomes the apiName via normalization (`API|JS|CDP|<Capital>` class prefix lowercased: `Page.click` → `page.click`; digits tolerated for bundler renames). Afterward user-visible frames are filtered (`filterStackFile` drops inspector/test-runner internals). The result feeds `_wrapApiCall`: apiName names the trace step; frames replace the error's stack so users see THEIR line, not `connection.ts`.
**Invariant:** The transition scan must run BEFORE filtering (filtered list would splice adjacent frames and corrupt the boundary); an apiName that looks internal (`_`-prefixed or contains `._`) is replaced by an explicit title in `_wrapApiCall` — never surface private method names as steps.
**Probe:** `grep -c "isPlaywrightLibrary" packages/playwright-core/src/client/clientStackTrace.ts` → `4`; `grep -c "normalizeAPIName" packages/playwright-core/src/client/clientStackTrace.ts` → `2` (def + call); `grep -n "apiName.startsWith('_')" packages/playwright-core/src/client/channelOwner.ts` → line 197.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "captureLibraryStackTrace", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI: `client.clientStackTrace.captureLibraryStackTrace ... clientStackTrace.ts 21-72`.)

## Verdict
Adopt deepest-transition apiName detection, prefix-based library tagging, and user-frame stack rewriting. Adapt `coreDir()` anchoring to your bundling layout (the regex already tolerates renamed classes) and your runtime's stack format outside V8. Omit the inspector-specific filtering unless you embed in an IDE. No dedicated unit test at this commit — behavior surfaces through every trace/error message in the library suite; keep the grep pins plus one manual "expect(e.stack).toContain('spec.ts')" assertion in your port battery.
