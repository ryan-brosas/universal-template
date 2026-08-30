<!-- capsule-v2 -->
# Prefix-laddered key validator — where should key-format validation live, and what does it return versus throw?

**Source:** pi-bailian MIT `main@c26c4e9855c87b18b17d5717b8c9171a27031d06`; Codebase Memory `pi-bailian`. **Question:** How do I structure API-key format validation so the error messages teach the user the fix?

## Four-rung validation ladder seam
**Path/Symbol:** `src/index.ts:validateApiKey` (:42-62).
**Signature:** `function validateApiKey(key: string): { valid: boolean; error?: string }`.
**Data Shape:** input trimmed first; result object carries at most one error string; rungs ordered trim → empty → prefix → length.

### Decisive source
```ts
  const trimmed = key.trim();

  if (!trimmed) {
    return { valid: false, error: "API key cannot be empty" };
  }

  if (!trimmed.startsWith("sk-sp-")) {
    return {
      valid: false,
      error:
        "Invalid API key format. Bailian Coding Plan API keys should start with 'sk-sp-'. Please get your key from https://modelstudio.console.alibabacloud.com/",
    };
  }

  if (trimmed.length < 10) {
    return { valid: false, error: "API key appears too short" };
  }

  return { valid: true };
```

**Flow:** whitespace tolerance first (paste-safe) → empty rejection with exact message `"API key cannot be empty"` → vendor-prefix check (`sk-sp-`) whose failure message embeds the console URL → minimum-length floor (10 chars incl. prefix) → `{valid:true}`.
**Invariant:** the VALIDATOR returns a result object and never throws; conversion to a thrown error happens only at the login boundary (`loginBailian` :97-100). Prefix rung dominates length rung: `"sk-sp-"` alone (6 chars) reports "too short", while `"sk-xxxxxxx"` (10 chars, wrong prefix) reports "Invalid format" — order matters.
**Probe:** `test/apikey.test.ts` (:36-117) pins all rungs incl. edge cases — whitespace-only (:63-67), wrong-prefix-but-long-enough (:88-92), bare-prefix `"sk-sp-"` → "appears too short" (:112-116), unicode/special-char keys accepted (:96-104). CAVEAT recorded in-source (:6-8): the function is unexported, so the test DUPLICATES the logic rather than testing the real symbol. Runner BLOCKED this pass (no node_modules); anchors are line-pinned reads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-bailian", query: "validate api key prefix format error", limit: 5, fields: ["signature", "lines"] });
```
Executed live at pin: returned `src.validateApiKey` (42-62), `test.apikey.test.validateApiKey` (14-34), `getApiKey` (120-122) — total 3, has_more false.

## Verdict
Adopt the ladder order (trim→empty→prefix→length), the result-object-at-validator/throw-at-login split, and remediation URLs inside error text. Adapt the prefix constant and messages to your vendor. Omit the unexported-symbol test duplication — export your validator and test the real one.
