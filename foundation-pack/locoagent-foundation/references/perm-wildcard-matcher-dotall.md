<!-- capsule-v2 -->
# Wildcard rule matcher — null-byte sentinels, single-star alignment, dotAll matching

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you compile a user-written wildcard permission pattern (`git *`, `npm run *`, `\*literal\*`) into a regex without letting escapes or regex metacharacters through?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/shellRuleMatching.ts` — `ShellPermissionRule` union (:25-37), `permissionRuleExtractPrefix` (:43-48), `hasWildcards` (:54-78), `matchWildcardPattern` (:90-154), `ESCAPED_STAR_PLACEHOLDER` (:14-15), `parsePermissionRule` (:159-184).
**Signature:** `matchWildcardPattern(pattern: string, command: string, caseInsensitive = false): boolean`; `parsePermissionRule(rule) → {type:'exact'|'prefix'|'wildcard', ...}`.
**Data Shape:** Rule taxonomy: legacy `cmd:*` suffix = PREFIX; any UNESCAPED `*` (even-backslash test, :62-77) elsewhere = WILDCARD; otherwise EXACT. Placeholders are NUL-wrapped strings (`\x00ESCAPED_STAR\x00`) — module-level so their RegExps compile once.

### Decisive source
```ts
// When a pattern ends with ' *' (space + unescaped wildcard) AND the trailing
// wildcard is the ONLY unescaped wildcard, make the trailing space-and-args
// optional so 'git *' matches both 'git add' and bare 'git'.
const unescapedStarCount = (processed.match(/\*/g) || []).length
if (regexPattern.endsWith(' .*') && unescapedStarCount === 1) {
  regexPattern = regexPattern.slice(0, -3) + '( .*)?'
}
```

**Flow:** parse (`:*` first → wildcards → exact) → in matchWildcardPattern: walk the pattern replacing `\*`/`\\` with sentinels → regex-escape everything EXCEPT `*` (`[.+?^${}()|[\]\\'"]`, :126) → turn bare `*` into `.*` → restore sentinels as escaped literals → apply the single-trailing-star alignment rewrite → anchor `^...$` with the **dotAll `s` flag** so wildcards span embedded newlines (heredoc content after command splitting).

**Invariant:** (1) The sentinel must be a byte sequence that cannot appear in user input (NUL bytes); escaping via plain placeholder strings is injectable. (2) The trailing-`*`-optional rewrite fires ONLY when that star is the sole unescaped one — multi-star patterns like `* run *` keep strict semantics or `npm run` would wrongly match. This aligns wildcard rules with prefix-rule behavior (`git:*`). (3) dotAll is security-relevant in BOTH directions: without it a deny rule fails to match newline-carrying commands. (4) Legacy `:*` is checked BEFORE wildcard detection and suppresses it (`endsWith(':*')` short-circuits hasWildcards).

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF "ESCAPED_STAR_PLACEHOLDER = '\\x00ESCAPED_STAR\\x00'" src/utils/permissions/shellRuleMatching.ts` → :14; `grep -nF "endsWith(' .*') && unescapedStarCount === 1" src/utils/permissions/shellRuleMatching.ts` → :143; `grep -nF "const flags = 's' + (caseInsensitive ? 'i' : '')" src/utils/permissions/shellRuleMatching.ts` → :150; graph search `matchWildcardPattern` → :90-154 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "matchWildcardPattern hasWildcards parsePermissionRule", limit: 5 });
```

## Verdict
Adopt the three-way rule taxonomy, even-backslash unescape counting, NUL-sentinel compilation, single-star alignment, and dotAll full-string anchoring. Adapt the suggestion builders to your settings destinations. Omit nothing else — the module is small and wholly reusable.
