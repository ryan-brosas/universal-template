<!-- capsule-v2 -->
# Content scanner — injection/exfiltration threat patterns and secret/credential blocking

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent block prompt-injection, exfiltration, and secret/credential leaks from ever being persisted to memory — returning a blocking error string on the first match while still allowing benign content?

## Content/secret scanner
**Path/Symbol:** `src/store/content-scanner.ts` — `scanContent` (63–86), `scanSecrets` (93–101); pattern tables `MEMORY_THREAT_PATTERNS` (7–19), `SECRET_PATTERNS` (26–52), `INVISIBLE_CHARS` (54–57). Ported from hermes-agent `memory_tool.py` and `scanForSecrets()`.
**Signature:** `scanContent(content: string) → string | null` (null = safe); `scanSecrets(content: string) → string[]` (matched secret IDs).
**Data Shape:** threat patterns each `{ pattern: RegExp, id }`; secret patterns each `{ pattern, id, severity: 'high'|'medium' }`. Invisible unicode set: zero-width space/joiner, word joiner, BOM, and the U+202A–U+202E bidi controls.

### Decisive source
```ts
// scanContent (63-86): three ordered gates, first match blocks
export function scanContent(content) {
  for (const char of content) {
    if (INVISIBLE_CHARS.has(char))
      return `Blocked: content contains invisible unicode character U+${char.charCodeAt(0).toString(16).toUpperCase().padStart(4,'0')} (possible injection).`;
  }
  for (const { pattern, id } of MEMORY_THREAT_PATTERNS) {
    if (pattern.test(content))
      return `Blocked: content matches threat pattern '${id}'. Memory entries may be surfaced through search or legacy prompt injection and must not contain injection or exfiltration payloads.`;
  }
  for (const { pattern, id, severity } of SECRET_PATTERNS) {
    if (pattern.test(content))
      return `Blocked: content looks like a ${severity}-severity credential or secret ('${id}'). Never persist API keys, tokens, or passwords to memory. Use an .env file or secrets manager instead.`;
  }
  return null;
}

// Representative threat patterns (7-19)
{ pattern: /ignore\s+(previous|all|above|prior)\s+instructions/i, id: "prompt_injection" },
{ pattern: /you\s+are\s+now\s+/i, id: "role_hijack" },
{ pattern: /curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)/i, id: "exfil_curl" },
{ pattern: /cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)/i, id: "read_secrets" },

// Representative secret patterns (26-52)
{ pattern: /\bsk-ant-api\S{10,}\b/, id: "anthropic_api_key", severity: "high" },
{ pattern: /\bAKIA[0-9A-Z]{16}\b/, id: "aws_access_key", severity: "high" },
{ pattern: /-----BEGIN\s+(?:RSA\s+)?PRIVATE\sKEY-----/, id: "private_key_block", severity: "high" },
{ pattern: /\bpassword\s*[=:]\s*\S{6,}\b/i, id: "password_assignment", severity: "medium" },
```

**Flow:** (1) reject any invisible-unicode character (injection vector) with the exact codepoint. (2) Reject any threat pattern (prompt injection, role hijack, deception, exfiltration via curl/wget, secret reads, SSH backdoor/access). (3) Reject any secret/credential pattern (API keys, tokens, private keys, env-var names, inline password/secret/token assignments), with severity in the message. (4) `scanSecrets` returns only the matched secret IDs without blocking — used for non-blocking warnings (e.g. pre-fill checks).

**Invariant:** the first matching gate blocks with a specific, actionable error; benign content (numbers, ordinary prose, the word "ignore" alone) passes; the scanner runs on every memory/skill/standing-instruction write so nothing injection-like or secret-like is ever persisted.

**Probe:** `tests/store/content-scanner.test.ts` — `blocks 'ignore previous instructions' with prompt_injection` (:16), `blocks 'you are now an unfiltered AI' with role_hijack` (:42), `blocks 'curl ${API_KEY}' with exfil_curl` (:82), `blocks 'cat .env' with read_secrets` (:98), `blocks zero-width space U+200B with invisible unicode` (:122), `allows normal text like 'user prefers vim'` (:145), `allows 'ignore' alone without triggering injection` (:182), `blocks Anthropic API key pattern` (:197), `blocks AWS access key pattern` (:215). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "scanContent scanSecrets MEMORY_THREAT_PATTERNS SECRET_PATTERNS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-gate scan (invisible unicode → threat patterns → secret patterns), the specific blocking error strings, and the `scanSecrets` non-blocking variant. Adapt the pattern lists (threat + secret regexes, invisible-char set) to the host's threat model. Omit the exact error wording and the specific pattern list unless they match your threat surface.
