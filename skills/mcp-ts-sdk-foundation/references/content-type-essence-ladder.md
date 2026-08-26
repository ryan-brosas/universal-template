<!-- capsule-v2 -->
# Content-type essence parsing — why must JSON detection parse the media type instead of substring-matching the header, and when does a malformed parameter section still pass?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How should a server classify `Content-Type` headers so parameters, case, and malformed values neither false-accept nor false-reject?

## Essence extractor
**Path/Symbol:** `packages/core-internal/src/shared/mediaType.ts`: `mediaTypeEssence` (:26-43), `isJsonContentType` (:51-57).
**Signature:** `mediaTypeEssence(header: string | null | undefined): string | undefined`; `isJsonContentType(header): boolean`.
**Data Shape:** returns lowercased `type/subtype` without parameters, or `undefined`; joined duplicate headers (comma in the tail) yield NO essence even if the first copy is clean.

### Decisive source
```ts
// :30-41 RFC 9110 parse first; browser-style fallback second
try {
    return contentType.parse(header).type;
} catch {
    const essence = (header.split(';', 1)[0] ?? '').trim().toLowerCase();
    // A comma in the parameter tail of an unparseable value indicates
    // joined duplicate headers — ambiguous, so no essence at all
    if (essence === '' || header.slice(essence.length).includes(',')) {
        return undefined;
    }
    return essence;
}
```

**Flow:** exact literal `'application/json'` fast-paths true (what SDK clients send every POST); otherwise parse → essence → compare. Malformed parameter sections (`application/json;`, `application/json; charset=`) still classify as application/json because browsers/HTTP stacks derive the type from the pre-`;` segment — rejecting those would break real clients. The doc comment names the failure being prevented: `text/plain; a=application/json` CONTAINS the substring but is text/plain.

**Invariant:** substring matching is wrong in BOTH directions — false-accepts parameter-carried lookalikes AND false-rejects case/parameter variants (`Application/JSON; charset=utf-8`). The duplicate-header comma rule keeps behavior uniform whether or not the first copy carries parameters: ambiguity ⇒ no classification rather than first-wins.

**Probe (direct tests):** `packages/core-internal/test/shared/mediaType.test.ts` — :6 'parses well-formed headers', :12 'falls back to the pre-parameter segment for malformed parameter sections', :26 'yields no essence for joined duplicate headers', :50 'never matches on substrings: parameters and sibling types are not application/json'.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "mediaTypeEssence isJsonContentType content type", limit: 3 });
```

## Verdict
Adopt the parse-fallback-comma ladder verbatim (pure, dependency-light modulo the `content-type` pkg); adapt the fast-path literal to your traffic; omit nothing.
