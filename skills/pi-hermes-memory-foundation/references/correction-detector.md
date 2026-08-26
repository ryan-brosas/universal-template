<!-- capsule-v2 -->
# Correction detector — two-pass filter that triggers an immediate memory save

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent detect when a user message is a correction and save it to memory immediately — using a two-pass strong/weak/negative pattern filter with directive-word gating, rate-limited to avoid spamming saves?

## Correction detection
**Path/Symbol:** `src/handlers/correction-detector.ts` — `isCorrection` (80–122), `setupCorrectionDetector` (124–287), `extractCorrectionDirective` (33–40), `compileCorrectionPatterns` (42–57), `hasDirectiveWord` (63–67). Pattern lists in `src/constants.ts` (`CORRECTION_STRONG_PATTERNS`, `CORRECTION_WEAK_PATTERNS`, `CORRECTION_NEGATIVE_PATTERNS`, `CORRECTION_DIRECTIVE_WORDS`).
**Signature:** `isCorrection(text: string, config?: {correctionStrongPatterns?, correctionWeakPatterns?, correctionNegativePatterns?, correctionDirectiveWords?}) → boolean`.
**Data Shape:** strong patterns always trigger; weak patterns trigger only if followed by a directive clause; negative patterns suppress even if a positive pattern matched. Directive words are verbs/"the/that/this" in the remainder after a weak-pattern match at index 0. Configured regex strings are compiled with `new RegExp(source, "i")`; invalid entries are ignored.

### Decisive source
```ts
// isCorrection (80-122): negative → strong → weak+directive
for (const pattern of negativePatterns) if (pattern.test(text)) return false;
for (const pattern of strongPatterns) if (pattern.test(text)) return true;
for (const pattern of weakPatterns) {
  if (pattern.test(text)) {
    const match = pattern.exec(text);
    if (match && match.index === 0) { // weak pattern must be at the start
      const remainder = text.slice(match[0].length).trim();
      if (hasDirectiveWord(remainder, directiveWords)) return true;
    }
  }
}
return false;

// hasDirectiveWord (63-67): word-boundary regex over the escaped directive words
const source = words.map(escapeRegexLiteral).join("|");
return new RegExp(`\\b(${source})\\b`, "i").test(remainder);

// extractCorrectionDirective (33-40): strip common correction starters
text.replace(/^(no|wrong|actually|stop|don'?t|that'?s not|I said|I told you)[,\.\s!]+/i, '')
    .replace(/^(please\s+)?/i, '').trim();
```

**Flow:** (1) On `message_end` with a user role, `isCorrection` runs the two-pass filter. (2) If negative patterns match, suppress. (3) If a strong pattern matches, trigger. (4) If a weak pattern matches at the start, trigger only when a directive word follows. (5) On `turn_end`, if a correction is pending and the rate limit (≥3 turns since last) allows, build a conversation snapshot, run the LLM save (direct transport or subprocess), and also save a `correction`-category failure memory with the extracted directive.

**Invariant:** a correction is only detected when a positive pattern is not suppressed by a negative one; weak patterns require a directive clause so "no just kidding" does not trigger; saves are rate-limited (max 1 per 3 turns) and never block the session on failure.

**Probe:** `tests/handlers/correction-detector.test.ts` — `matches 'don't do that'` (:26), `matches 'no, use yarn instead' (has directive 'use')` (:58), `matches 'wrong, the file is in src/' (has directive 'the')` (:62), `does NOT match 'no just kidding' (no directive clause)` (:78), `suppresses 'no worries, I'll handle it'` (:86), `suppresses 'stop for now'` (:122), `does NOT match 'yes, do that'` (:130), `does NOT match 'looks good'` (:134). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "isCorrection setupCorrectionDetector extractCorrectionDirective hasDirectiveWord", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-pass strong/weak/negative filter with directive-word gating, the rate-limited immediate save, and the directive extraction. Adapt the pattern lists, the directive-word list, and the rate-limit constant to the host. Omit the Pi `message_end`/`turn_end` hook wiring, the LLM save transport, and the failure-memory write unless a target has the same extension event model.
