<!-- capsule-v2 -->
# Dual-format CLI argument parsing — how do you accept a space-separated `args` string while keeping legacy comma-separated users working?

**Source:** qodana-action Apache-2.0 `main@829c6a5644d4d52f7d742ac90c695c506053883b`; Codebase Memory `qodana-action`. **Question:** A CI input carries a single string of CLI flags. How does the action parse BOTH `--log-level debug` and legacy `-l,qodana-jvm,--property,a=b,c` without corrupting comma-bearing values?

## Format auto-detect over shell-quote tokenization
**Path/Symbol:** `common/utils.ts:parseRawArguments` (:222-236), `looksLikeCommaSeparated` (:102-125), `parseSpaceSeparated` (:130-133), `parseCommaSeparated` (:139-185), `warnDeprecatedCommaFormat` (:190-205).
**Signature:** `parseRawArguments(rawArgs: string): string[]`.
**Data Shape:** Input = one raw string from any CI surface (GitHub `args:` input, GitLab `QODANA_ARGS`, VSTS `args`). Output = argv array consumed by `getQodanaScanArgs`/`getQodanaPullArgs`/`extractArg`.

### Decisive source
```ts
export function parseRawArguments(rawArgs: string): string[] {
  if (!rawArgs || !rawArgs.trim()) {
    return []
  }
  const spaceParsed = parseSpaceSeparated(rawArgs.trim())
  if (looksLikeCommaSeparated(spaceParsed)) {
    const commaParsed = parseCommaSeparated(rawArgs)
    warnDeprecatedCommaFormat(rawArgs, commaParsed)
    return commaParsed
  }
  return spaceParsed
}

function parseSpaceSeparated(input: string): string[] {
  const parsed = shellParse(input, () => undefined) // disable env expansion
  return parsed.filter((entry): entry is string => typeof entry === 'string')
}
```

**Flow:** trim → tokenize with `shell-quote` with env expansion DISABLED (callback returns undefined so `$VAR` never interpolates) → run the token list through four comma heuristics: standalone `,`; token starting `,--flag` (`/^,\s*-{1,2}\w/`, anchored to avoid false positives like `--property=list=-1,-2,-3`); flag ending with comma (`/^-{1,2}\w[^,]*,/`); bare value with trailing comma from multiline YAML (`/^[^-=][^=]*,$/`) → if ANY heuristic hits, re-parse the ORIGINAL raw string with the comma path and emit a deprecation warning showing Current vs Suggested quoting → else return the space-parsed tokens.
**Invariant:** The comma path has a carve-out that a porter WILL get wrong: inside `parseCommaSeparated`, everything after a `--property` token up to the next token starting with `-` is re-joined with commas into ONE value (`result.push(propertyValues.join(','))`), so `--property,key=val1,val2,val3` stays a single argv element while every other comma becomes an argument separator. Space-format detection must treat `key=a,b,c` after `--property` as NOT legacy (test `'commas in property values do not trigger legacy detection'`).
**Probe:** `common/__tests__/main.test.ts` `describe('parseRawArguments')` :250-548 — space table (:251-341), quoted args incl. unclosed-quote-rest-is-quoted (:343-401), legacy comma table asserting warningMessage contains 'deprecated' (:403-524), multiline YAML trailing-comma case (:504-516), edge cases :526-548.
**Coverage caveat:** no runtime runner in this workspace; probe pinned by line range, deterministic grep checks executed instead.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "parseCommaSeparated looksLikeCommaSeparated legacy format", limit: 6 });
// resolves parseCommaSeparated common/utils.ts:139-185 (+ the checked-in bundle twin vsts/QodanaScan/index.js)
```

## Verdict
Adopt the auto-detect + deprecation-warning pattern and the `--property` comma-preserving carve-out verbatim for any user-typed flag string ported across a CI boundary; adapt the warning channel via `setDeprecationWarningCallback` (console.warn default; each app registers its platform emitter at module load). Omit nothing — the whole file is the contract. Note for porters: `vsts/QodanaScan/index.js` (82k-line webpack bundle) contains compiled copies of these functions; it is build output, not a second source of truth.
