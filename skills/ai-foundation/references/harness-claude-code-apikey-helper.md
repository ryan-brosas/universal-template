<!-- capsule-v2 -->
# Claude Code apiKeyHelper mirror — how do you mirror a CLI's password-manager credential hook without becoming an injection vector?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory MCP NOT connected this session → direct source+test read fallback per AGENTS.md. **Question:** the `claude` CLI lets users fetch credentials from password managers through an `apiKeyHelper` command in `~/.claude/settings.json` — how do you honor that hook from a harness without weakening the credential ladder?

## Last-resort executable hook, fail-soft at every rung
**Path/Symbol:** `packages/harness-claude-code/src/claude-code-auth.ts` — `readApiKeyHelper` :186–212, `pickAnthropic` :158–178, `ResolveClaudeCodeEnvOptions` :78–85; injection seam `options.readApiKeyHelper` (:94: `const readApiKey = options.readApiKeyHelper ?? readApiKeyHelper`).
**Signature:** `readApiKeyHelper(): string | undefined`; consumed as `const helperKey = explicit ? undefined : readApiKey(); const apiKey = explicit?.apiKey ?? processEnv.ANTHROPIC_API_KEY ?? helperKey;` (same for `ANTHROPIC_AUTH_TOKEN`).
**Data Shape:** settings file `{ apiKeyHelper?: unknown }`; the command must be a non-empty string; output is trimmed and must be non-empty.

### Decisive source
```ts
// claude-code-auth.ts :180–212 — the mirror, verbatim rationale + fail-soft body
/**
 * Read the `apiKeyHelper` setting from `~/.claude/settings.json` and run
 * it. The `claude` CLI uses this hook to fetch credentials from password
 * managers and similar tools; mirroring it here lets users with that
 * setup run the harness without having to set `ANTHROPIC_API_KEY`
 * explicitly.
 */
function readApiKeyHelper(): string | undefined {
  const home = homedir();
  if (!home) return undefined;
  let raw: string;
  try { raw = readFileSync(join(home, '.claude', 'settings.json'), 'utf8'); }
  catch { return undefined; }
  let settings: { apiKeyHelper?: unknown };
  try { settings = JSON.parse(raw); } catch { return undefined; }
  const command = settings.apiKeyHelper;
  if (typeof command !== 'string' || command.length === 0) return undefined;
  try {
    const output = execFileSync('sh', ['-c', command], {
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'],
    });
    const trimmed = output.trim();
    return trimmed.length > 0 ? trimmed : undefined;
  } catch { return undefined; }
}
```

**Flow:** the helper is consulted ONLY in the ambient-direct branch of `resolveClaudeCodeEnv` — explicit `auth.anthropic` skips it entirely (`helperKey = explicit ? undefined : readApiKey()`), gateway selection never reaches it, and static env keys win over it (`processEnv.ANTHROPIC_API_KEY ?? helperKey`). One helper invocation fills BOTH `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` when neither static value exists (test "populates both ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN from the apiKeyHelper"), so the resulting env drives both header shapes of `createClaudeCodeRequestTransformations` (`x-api-key` + `Authorization: Bearer`). The injection seam `readApiKeyHelper` option exists so tests (and hosts) can substitute the executable probe — every test passes `readApiKeyHelper: noHelper` except the two helper-focused cases.
**Invariant:** every failure mode is fail-soft to `undefined` (missing home, unreadable file, invalid JSON, non-string/empty command, exec failure, empty output) — the helper can only ADD a credential, never break resolution; the command runs synchronously via `execFileSync` with stdio reduced to `['ignore','pipe','ignore']` so a chatty helper cannot pollute stderr; precedence is explicit auth > static env > helper, matching the claude CLI's own behavior (documented in the option's JSDoc).
**Probe:** direct test `claude-code-auth.test.ts` 249L read whole-file (19 cases): "forwards a base URL alongside the apiKeyHelper-supplied credentials" and "populates both ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN from the apiKeyHelper" pin the fill-both shape; "prefers a static ANTHROPIC_API_KEY over the apiKeyHelper" pins precedence with a `vi.fn` helper. Deterministic probes: `grep -n "execFileSync('sh', ['-c', command]" packages/harness-claude-code/src/claude-code-auth.ts` → :204; `grep -c "readApiKeyHelper: noHelper" packages/harness-claude-code/src/claude-code-auth.test.ts` → `17`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "apiKeyHelper settings.json credential helper exec password manager", limit: 10 });
```
Graph MCP absent this session — file-level analog: naive "credential helper" queries hit only gateway-auth symbols; GREEN: `readApiKeyHelper` resolves to exactly one defining file (:186) plus its test injection seam.

## Verdict
Adopt: last-resort executable hook with fail-soft rungs, static-env precedence, fill-both-credential-slots output handling, and an injectable seam for tests. Adapt the settings path/command key to your CLI's contract. Omit nothing structural — but if your host cannot execute arbitrary user-configured commands, drop the hook and keep the injectable seam so embedders can supply their own source.
