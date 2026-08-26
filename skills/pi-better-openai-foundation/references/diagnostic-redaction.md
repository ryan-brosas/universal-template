<!-- capsule-v2 -->
# Diagnostic redaction — strip ANSI/control chars and redact secret-like fields from diagnostic text and structured values

**Source:** pi-better-openai (MIT, `main@86814e9047996abba08e4c907e23286329196fe0`); Codebase Memory `pi-better-openai`. **Question:** How does an extension sanitize error/diagnostic text and recursively redact secret-like fields so credentials never leak into logs or the UI, while preserving readable structure and bounding length?

## Diagnostic secret redaction
**Path/Symbol:** `src/format.ts:sanitizeDiagnosticError` (64–81), `redactDiagnosticValue` (93–104), `maskIdentifier` (57–62), `stripAnsi` (33–35), `replaceControlCharacters` (24–31); helpers `formatTokens` (45–51), `sanitizeStatusText` (53–55). Constants `ANSI_ESCAPE_PATTERN` (6), `DIAGNOSTIC_MAX_LENGTH` (8), `REDACTED` (9), `SENSITIVE_DIAGNOSTIC_KEY_SUFFIXES` (10–22).
**Signature:** `sanitizeDiagnosticError(message: string, maxLength = 500): string`; `redactDiagnosticValue(value: unknown): unknown`; `maskIdentifier(value: string | undefined): string | undefined`.
**Data Shape:** `sanitizeDiagnosticError` returns a single-line, control-char-stripped, secret-redacted string capped at `maxLength` (default 500) with `…` truncation. `redactDiagnosticValue` recursively maps strings through `sanitizeDiagnosticError`, arrays element-wise, and objects field-wise, replacing any value whose key matches a sensitive suffix with the literal `[REDACTED]`. `maskIdentifier` returns `"found"` for short values, else `first4...last4`.

### Decisive source
```ts
// sanitizeDiagnosticError: strip ANSI, then redact embedded credentials
stripAnsi(message)
  .replace(/\bBearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]")
  .replace(/\bsk-[A-Za-z0-9_-]{8,}\b/g, "sk-[REDACTED]")
  .replace(/\bacct_[A-Za-z0-9_-]{6,}\b/g, "acct_[REDACTED]")
  .replace(/(["']?(?:access|access_token|token|api[_-]?key|authorization|accountId|account_id)["']?\s*[:=]\s*["']?)([^"',\s}\]]+)/gi, "$1[REDACTED]")
  .replace(/\[REDACTED\](?:\])+/g, "[REDACTED]");
const redacted = replaceControlCharacters(redactedSecrets).replace(/ +/g, " ").trim();
return redacted || "Unknown error.";  // then truncate to maxLength with …

// redactDiagnosticValue: recursive; sensitive key => [REDACTED]
isSensitiveDiagnosticKey(key) ? REDACTED : redactDiagnosticValue(entry)
// isSensitiveDiagnosticKey: normalized key equals access/auth/refresh or ends with a sensitive suffix
```

**Flow:** (1) strip ANSI escape sequences; (2) redact `Bearer <token>`, `sk-...`, `acct_...`, and `key: value` credential pairs; (3) collapse stray `[REDACTED]]` runs; (4) replace control characters with spaces and collapse whitespace; (5) fall back to `"Unknown error."` if empty; (6) truncate to `maxLength` with a trailing `…`; (7) `redactDiagnosticValue` applies this per-string and replaces sensitive-keyed fields wholesale.

**Invariant:** no ANSI/control characters survive; any value under a sensitive key (token/apiKey/authorization/password/secret/credential/accountId, etc.) is replaced with `[REDACTED]`; the output never exceeds `maxLength`; an empty input never yields an empty string.

**Probe:** `tests/format.test.ts` — `truncates ansi-styled text to visible width` (`truncateToWidth("\u001b[2mabcdef\u001b[22m", 4)` → visible width 4, `stripAnsi` → `"a..."`); `measures and truncates Unicode by terminal cell width` (`visibleWidth("界")===2`, `visibleWidth("🙂")===2`); `redacts secret-like fields and embedded credentials in diagnostic values` (nested `accountId`/`refresh`/`accessKey` → `[REDACTED]`, `note`'s `Authorization: Bearer ...` → `Authorization: Bearer [REDACTED]`). Also `tests/usage.test.ts` (`maskIdentifier("acct_1234567890abcdef")` → `"acct...cdef"`; `sanitizeDiagnosticError` caps length ≤500). Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so these probes are source-grounded from the on-disk test files, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "sanitizeDiagnosticError redactDiagnosticValue maskIdentifier stripAnsi", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ANSI/control stripping, the embedded-credential regex redaction, the recursive sensitive-key redaction, the length cap, and the `maskIdentifier` first4...last4 pattern. Adapt the sensitive-key suffix list and the exact credential regexes to the host's token formats. Omit the pi-tui `visibleWidth`/`truncateToWidth` wrappers (use the host's terminal-width primitive) unless a target needs them.
