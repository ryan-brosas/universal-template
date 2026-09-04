<!-- capsule-v2 -->
# Stale-test mirror trap — when a "direct test" re-implements the function instead of importing it, it pins nothing

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** How can a porter detect that a passing upstream test suite does NOT actually cover the production code it names — before trusting it as gate-5 evidence?

## The vacuous-suite detector
**Path/Symbol:** `tests/backend/claude.test.ts` : local function `toClaudeReasoningTokens` (:8-16) vs production `src/backend/claude.ts` : `toClaudeReasoningTokens` (:16-27). File header: *"Direct implementation of toClaudeReasoningTokens for testing purposes. Mirrors the implementation in src/backend/claude.ts"*.
**Signature:** both `function toClaudeReasoningTokens(reasoning): string` — but the copies DISAGREE.
**Data Shape:** production maps low→`'15999'`/medium→`'31999'`/high→`'63999'`; the test's mirror asserts low→`'7999'`/medium→`'15999'`/high→`'31999'` ("8k-1 multiples" ladder, one octave lower).

### Decisive source
```ts
// src/backend/claude.ts:19-23  (PRODUCTION TRUTH at pin c3c69f2)
case 'minimal': return '0';
case 'low':     return '15999';     // 16k-1
case 'medium':  return '31999';    // 32k-1
case 'high':    return '63999';    // 64k-1
case 'xhigh':   return '63999';    // 64k-1   <- xhigh==high, NOT unique
```
```ts
// tests/backend/claude.test.ts:11-15  (STALE MIRROR the suite actually runs)
case 'minimal': return '0';
case 'low':     return '7999';      // 8k-1
case 'medium':  return '15999';     // 16k-1
case 'high':    return '31999';     // 32k-1
case 'xhigh':   return '63999';     // 64k-1
```

**Flow:** the suite imports NOTHING from `src/backend/claude.ts` — all nine tests execute the frozen in-file copy, so `bun test tests/backend/claude.test.ts` reports **9 pass / 0 fail while asserting values production no longer returns**. The comment claiming to "mirror" the implementation is the rot vector: any production change silently invalidates the mirror without failing a single assertion. Also note production collapses xhigh AND max onto 63999 while the mirror keeps xhigh distinct — the "all values are unique" test would FAIL against real production behavior.
**Invariant:** a test that re-implements instead of imports provides ZERO regression coverage for the named symbol; its greenness is not evidence about the source. Gate discipline for porters: grep the test file for an import of the module under test (`import ... from '../../src/backend/claude'`) BEFORE citing it as the direct-test Probe; if absent, downgrade the probe to a source-range pin and say so. Contrast: `tests/backend/pi.test.ts` imports `toPiTools` etc. from source and is a REAL pin.
**Probe:** deterministic — `grep -n "^import" tests/backend/claude.test.ts` shows only `bun:test`; then compare `grep -n "return '" src/backend/claude.ts` against `grep -n "toBe('" tests/backend/claude.test.ts` → divergent ladders. Runner evidence: `bun test tests/backend/claude.test.ts` = 9 pass / 0 fail at pin c3c69f2 (vacuously).
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"MAX_THINKING_TOKENS reasoning tokens claude","limit":5,"detail":"ids"}'
```
→ resolves the production mapper `toClaudeReasoningTokens` in `src/backend/claude.ts` :16-27.

## Verdict
Adopt the DETECTION RULE (mirror-header + missing-import grep) as process; adopt the production ladder (0 / 16k-1 / 32k-1 / 64k-1 / 64k-1 / 64k-1 with env var `MAX_THINKING_TOKENS`) only if you port the claude backend. Omit the stale mirror values — they are wrong relative to production. Caveat recorded verbatim from source read at pin c3c69f2.
