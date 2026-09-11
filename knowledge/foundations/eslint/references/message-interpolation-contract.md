<!-- capsule-v2 -->
# Placeholder interpolation contract — how do you substitute {{ tokens }} in user-facing messages without leaking partial data?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What are the exact semantics of message placeholder substitution, and how do testers detect placeholders the rule FAILED to fill?

## interpolate + getPlaceholderMatcher
**Path/Symbol:** `lib/linter/interpolate.js:getPlaceholderMatcher()` (:17–19), `interpolate(text, data)` (:28–47).
**Signature:** `getPlaceholderMatcher(): /\{\{([^{}]+)\}\}/gu` (fresh regex each call — global regexes are stateful); `interpolate(text, data?): string`.
**Data Shape:** placeholder names are trimmed (`{{ name }}` ≡ `{{name}}`); missing keys leave the token UNTOUCHED; values stringify via JS template coercion.

### Decisive source
```js
if (!data) return text;                       // null/undefined data = passthrough
return text.replace(matcher, (fullMatch, termWithWhitespace) => {
  const term = termWithWhitespace.trim();
  if (term in data) return data[term];
  return fullMatch;                           // "Preserve old behavior: don't replace"
});
```

**Flow:** match-all → trim captured name → own/inherited `in` check → substitute or preserve.
**Invariant:** non-replacement of unknown keys is a deliberate COMPATIBILITY freeze: literal text like "{{ see docs }}" must survive into output rather than vanish. The `[^{}]+` inner pattern forbids nesting so `{{a{{b}}}}` cannot mis-capture. Values coerce through String() semantics — objects become "[object Object]" unless they define toString (test-pinned, including BigInt and Set/Map). Because the matcher is `/g`, it MUST be created per call (shared lastIndex corruption); the exported factory exists precisely to make that easy.
**Probe:** `tests/lib/linter/interpolate.js` (:17–43 matcher behavior incl. no-match passthrough; :46–62 trimmed-key interpolation; :64–85 stringification matrix).

## Unsubstituted-placeholder detection (tester side)
**Path/Symbol:** `lib/rule-tester/rule-tester.js:getMessagePlaceholders(message)` (:334) + `getUnsubstitutedMessagePlaceholders(message, raw, data)` (:348).
**Flow:** placeholders remaining AFTER interpolation are matched against the RAW meta.messages template minus provided data keys — only names present in raw AND absent from data count as failures.
**Invariant:** the intersection filter kills false positives from literal `{{...}}` text that was never meant as a placeholder.
**Probe:** `tests/lib/rule-tester/rule-tester.js` ("unsubstituted placeholders" assertion messages throughout the suggestion/data suites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "interpolate getPlaceholderMatcher getUnsubstitutedMessagePlaceholders", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.interpolate.interpolate" });
```

## Verdict
Adopt trim-then-in-check + preserve-on-missing verbatim for any templated diagnostic system; adapt delimiters; keep the fresh-regex discipline.
