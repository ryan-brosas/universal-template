<!-- capsule-v2 -->
# Agent self-install bootstrap — how does an agent skill install and build its own tool on first use?

**Source:** aeo-affiliate-skills MIT `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory `aeo-affiliate-skills`. **Question:** A skill ships with a compiled binary it depends on — what exact instruction ladder lets an autonomous agent find, build, and use it without a human reading a README?

## Path-probe ladder → NEEDS_SETUP sentinel → approval-gated one-time build
**Path/Symbol:** root `SKILL.md` SETUP block (:19–39), frontmatter `allowed-tools: [Bash, Read]` (:9–11), Architecture contract section (:101–107); build command source `package.json` `build` script (`bun build --compile tools/src/cli.ts --outfile tools/dist/affiliate-check`).
**Signature:** bash probe (agent-executed):
```bash
if test -x .claude/skills/affiliate-skills/tools/dist/affiliate-check; then
  A=.claude/skills/affiliate-skills/tools/dist/affiliate-check
elif test -x ~/.claude/skills/affiliate-skills/tools/dist/affiliate-check; then
  A=~/.claude/skills/affiliate-skills/tools/dist/affiliate-check
else
  echo "NEEDS_SETUP"
fi
```
**Data Shape:** `A` = resolved binary path used verbatim by every later command example (`$A search "AI video tools"`). Setup branch requires user approval before the ~10 s build (`cd <SKILL_DIR> && ./setup`), plus a bun-install fallback (`curl -fsSL https://bun.sh/install | bash`).

### Decisive source
```markdown
If `NEEDS_SETUP`:
1. Tell the user: "affiliate-check needs a one-time build (~10 seconds). OK to proceed?"
2. If approved, run: `cd <SKILL_DIR> && ./setup`
3. If `bun` is not installed: `curl -fsSL https://bun.sh/install | bash`
```

…with the contract the agent can rely on after setup:

```markdown
- Persistent Bun daemon on localhost (port 9500-9510)
- In-memory cache with 5-minute TTL
- State file: `/tmp/affiliate-check.json`
- Auto-shutdown after 30 min idle
- Server crash → auto-restarts on next command
```

**Flow:** skill activation → probe project-level install, then user-level → if found, set `A` once and reuse for all commands; if not, surface the NEEDS_SETUP sentinel to the agent, ask ONE approval question stating cost (~10 s), build via repo-owned `./setup`, fall back to installing bun when absent. The skill's frontmatter restricts itself to Bash+Read so the whole ladder is executable by tool-permission alone; the daemon properties (ports, TTL, state file, idle shutdown) are stated in the skill so the agent never has to discover them empirically.
**Invariant:** The binary path is resolved ONCE per session into `A` and every subsequent snippet assumes `$A` — instructions must never re-probe mid-session or mix bare/binary-prefixed commands. The build is gated behind explicit user consent because it executes an arbitrary-repo script; the sentinel string gives agents a crisp machine-detectable branch point instead of prose parsing.
**Probe:** Source pins: `grep -n "NEEDS_SETUP\|test -x" SKILL.md` at checkout root → :25/:27/:30; `grep -n '"build"' package.json` → :6 compile line proving `tools/dist/affiliate-check` is the artifact the probes target.
**Coverage caveat:** none — root `SKILL.md` and `package.json` checked `no_recorded_issue` at generation 2026-08-25T08:24:56Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aeo-affiliate-skills", query: "setup binary dist affiliate-check allowed-tools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape for any skill that bundles a tool: two-level install-path probe → machine-readable missing sentinel → single approval-gated bootstrap step naming its cost → dependency fallback → document the runtime contract (ports/TTL/state) inside the skill so agents need zero code archaeology. Adapt paths/permission names to your host's convention. Omit the curl|bash fallback in security-sensitive ports — gate it behind the same explicit approval as the build, or require a package-manager install instead.
