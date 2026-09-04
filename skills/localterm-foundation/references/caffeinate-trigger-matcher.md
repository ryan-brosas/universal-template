<!-- capsule-v2 -->
# Caffeinate trigger matcher — does this command line count as a recognized keep-awake program?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I match a process command line against short trigger names without substring false-positives and without missing real package layouts?

## Token-basename + path-segment matching ladder
**Path/Symbol:** `packages/server/src/caffeinate-process-match.ts:commandMatchesTriggers` (30–49) with helper `firstMatchingTrigger` (13–19); tree walk `anySessionRunsTrigger` (54–81); snapshot `defaultSnapshotProcesses` (89–113).
**Signature:** `commandMatchesTriggers(command: string, triggers: ReadonlySet<string>): string | null`; `anySessionRunsTrigger(sessionPids, snapshot, triggers): string | null`.
**Data Shape:** triggers lowercased set; command = full ps command line; returns the MATCHED trigger (lowercased) or null. Snapshot entries `{pid, ppid, command}` from one `ps -A -o pid=,ppid=,command=` call (maxBuffer 8MB; resolves [] on any failure — caffeinate stays as-is).

### Decisive source
```ts
// :13-29 — exact-match only; three-tier per-token ladder
const firstMatchingTrigger = (raw, triggers) => {
  const lowered = raw.toLowerCase();
  if (triggers.has(lowered)) return lowered;
  const stripped = lowered.replace(SCRIPT_EXTENSION_RE, "");
  if (stripped !== lowered && stripped && triggers.has(stripped)) return stripped;
  return null;
};
// Matching strategy:
//   1. basename exact
//   2. basename with common script extension stripped  (`codex.js` -> `codex`)
//   3. any full `/`-delimited path segment exact         (`claude/versions/2.1.178` -> `claude`)
```

**Flow:** split command on whitespace → per token: basename match (tier 1), extension-stripped basename (`\.(js|mjs|cjs|ts|tsx|jsx|py|sh|pl|rb)$i`, tier 2), then every directory segment left of the last slash (tier 3). Tree walk BFS from each session shell pid over a ppid→children index; roots (the shells) are pre-seeded into `visited` so their own command is NEVER matched; first descendant whose command matches wins. Truncation of long command lines by terminal width is harmless — only leading binary tokens matter.
**Invariant:** whole-segment equality everywhere — `pi` never matches inside `raspimon`, `/opt/not-claude/bin/run`, or `pinetry` (substring matching would be the wrong port); extension stripping applies to script extensions ONLY (a bare binary named `codex.js` shim still matches via tier 2); empty trigger set ⇒ null immediately.
**Probe:** `packages/server/tests/caffeinate-process-match.test.ts::"matches a versioned binary by a parent directory segment"` (:35), `"does not match a trigger as a substring of a path segment"` (:39 — incl. raspimon/pi case), `"never matches the session shell itself"` (:84), `"walks deeper descendants, not just direct children"` (:75).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "commandMatchesTriggers", limit: 5, fields: ["signature", "name", "file"] });
// → commandMatchesTriggers @ caffeinate-process-match.ts:30-49 (exact)
```

## Verdict
Adopt the three-tier ladder + visited-seeded BFS verbatim (both are pure functions); adapt SCRIPT_EXTENSION_RE vocabulary to host script runtimes; omit the ps invocation if the host exposes procfs/enumeration natively (keep the resolve-to-[] failure shape). Direct tests pin every tier at this commit.
