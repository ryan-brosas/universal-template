<!-- capsule-v2 -->
# agent-browser CDP pin — how do you stop a browser CLI from silently spawning its own throwaway browser instead of attaching to yours?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you guarantee every CLI invocation of an external automation tool attaches to the ONE browser holding the real login session — and fails fast rather than falling back?

## Config-file pin with idempotent, write-only-on-change sync
**Path/Symbol:** `scripts/lib/agent-browser-config.ts`:`syncAgentBrowserConfig`, `agentBrowserConfigPath` (`:22-53`).
**Signature:** `syncAgentBrowserConfig(projectRoot: string, port: number): string` (returns config path).
**Data Shape:** Project-root file `agent-browser.json` with merged keys; the pin key is `cdp: "<port>"` — a STRING. agent-browser rejects an integer for this key ("invalid type: integer"). Config search order of the tool: `~/.agent-browser/config.json` < `./agent-browser.json` (cwd) < env < flags.

### Decisive source
```ts
const next = { ...current, cdp: String(port) }
// Stable 2-space formatting + trailing newline so re-runs are idempotent.
const rendered = JSON.stringify(next, null, 2) + '\n'
if (!existsSync(path) || readFileSync(path, 'utf-8') !== rendered) {
  writeFileSync(path, rendered)
}
```
with malformed-file recovery:
```ts
try {
  const parsed = JSON.parse(readFileSync(path, 'utf-8'))
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) current = parsed
} catch { /* malformed file → rewrite it from scratch with just the pin */ }
```

**Flow:** read existing config (malformed ⇒ start clean) → merge ONLY the pin key, preserving user keys → render deterministically → write only when content differs → also point `AGENT_BROWSER_CONFIG` at the file via env so the pin holds regardless of each command's cwd.
**Invariant:** The failure mode being prevented: unconfigured, agent-browser launches its OWN bundled "Chrome for Testing" on a random port, so social logins land in a throwaway profile that can never stay signed in. With the pin, EVERY command (even a bare `open`) attaches to the CDP port, and a down port fails FAST with "Timeout connecting to CDP" instead of silently spawning a fresh browser. Never let a fallback-to-fresh-browser path exist.
**Probe:** `scripts/lib/agent-browser-config.test.ts` — `writes cdp as a STRING (agent-browser rejects integers)` (:11), `preserves other keys and updates the port` (:19), `is idempotent — stable formatting, no rewrite churn` (:28), `recovers from a malformed file` (:37).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "syncAgentBrowserConfig cdp pin", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the pin pattern (config-file default override + fail-fast), string-typed port, preserve-other-keys merge, byte-identical idempotent writes. Adapt the config filename/key names to whichever automation CLI your host uses. Omit nothing here — the write-only-on-change rule is what keeps default-port users' git trees clean.
