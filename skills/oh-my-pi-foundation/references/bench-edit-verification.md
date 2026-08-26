<!-- capsule-v2 -->
# Edit verification pipeline — format-normalized equivalence with blank-line sensitivity and whitespace-restore

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you verify an agent's edited output against expected fixtures so that formatting and stray blank-line noise never fail a correct edit, while real content differences (including blank-line-significant formats) always do?

## verifyExpectedFileSubset — normalize → restore → format → compare
**Path/Symbol:** `packages/typescript-edit-benchmark/src/verify.ts` — `verifyExpectedFileSubset` (85-183), `verifyExpectedFiles` (81-83, thin wrapper), `restoreWhitespaceOnlyLineDiffs` (273-316), `normalizeBlankLines` (247-249), `blankLineSensitive` (259-261), `stripBlankLines` (264-271), `createCompactDiff` (33-79), `computeIndentScore` (202-240), `computeDiffStats` (185-200).
**Signature:** `verifyExpectedFileSubset(expectedDir, actualDir, files?): Promise<VerificationResult>`; `VerificationResult = { success, error?, duration, indentScore?, formattedEquivalent?, diffStats?, diff? }`.
**Data Shape:** `files` undefined ⇒ compare the FULL fixture set (missing **and** extra files both fail); `files` given ⇒ subset compare where ONLY missing files fail (extras tolerated). `indentScore` = mean per-file `computeIndentDistanceForDiff(actualRaw, actualFormatted)` — how much the formatter had to fix the agent's indentation (tabs count 2, spaces 1). `diffStats = { linesChanged, charsChanged }`.

### Decisive source
```ts
const expectedNormalized = normalizeLineEndings(expectedRaw);          // \r\n? → \n
const actualNormalized   = normalizeLineEndings(actualRaw);
const actualWithWS       = restoreWhitespaceOnlyLineDiffs(expectedNormalized, actualNormalized);
const expectedFormatted  = await formatContent(expectedPath, normalizeBlankLines(expectedNormalized));
const actualFormatted    = await formatContent(actualPath,   normalizeBlankLines(actualWithWS));
const formattedEquivalent = blankLineSensitive(file)
    ? expectedFormatted.formatted === actualFormatted.formatted
    : stripBlankLines(expectedFormatted.formatted) === stripBlankLines(actualFormatted.formatted);
```
**Flow:** list expected fixture files + actual files → if `files` names any file absent from the fixture, fail immediately (metadata lies) → missing files fail always; extra files fail only when `files===undefined` → per file: normalize line endings → **restore whitespace-only line diffs** (a removed line that equals an added line ignoring whitespace is replaced by the *expected* line, so an indent-only drift collapses to the expected text; unmatched adds stay, unmatched removes drop; trailing-newline preserved) → collapse 2+ blank lines to one (`normalizeBlankLines`) → Prettier-format both sides → compare: blank-sensitive formats (`.md/.mdx/.yml/.yaml`) need exact formatted equality; code formats strip blank lines before comparing → on mismatch emit a compact context diff (`@@` hunks with 3 context lines, `+`/`-` rows) + stats + per-file indentScore → success aggregates mean indentScore.
**Invariant:** the whitespace-restore pass runs on RAW content BEFORE formatting, and only a removed/added pair that is whitespace-equivalent is collapsed to the expected side — so a real content change can never be masked, and an indent-only drift never surfaces as `+`/`-` rows. Blank lines are semantically significant ONLY for markdown/yaml/mdx; for code they are noise that formatting alone cannot repair (Prettier preserves single blank lines), hence the explicit strip.

**Probe:** `packages/typescript-edit-benchmark/test/verify.test.ts` — `:96-114` pins the stray-seam-blank tolerance for code (`function a(){}` vs `function a(){}\n\nfunction b(){}` still passes); `:116-129` pins that markdown blank lines stay significant (one paragraph vs two FAILS); `:145-157` pins whitespace-only diff tolerance on non-formatted files; `:159-201` pins that an inserted line + indent drift reports only the insertion (`const inserted` present, `a:`/`b:` absent) when Prettier bails on a syntax error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "verifyExpectedFileSubset restoreWhitespaceOnlyLineDiffs blankLineSensitive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole pipeline for any output-equivalence checker: normalize → restore whitespace-only diffs → collapse blanks → format → blank-sensitive compare. Adapt the Prettier parser map and blank-sensitive extension set to your formats; omit the OMP-specific `Bun.file` I/O. The whitespace-restore-before-format ordering and the code-vs-markdown blank sensitivity split are the invariants porters get wrong — both test-pinned.
