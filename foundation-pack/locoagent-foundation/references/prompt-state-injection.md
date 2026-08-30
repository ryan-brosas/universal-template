<!-- capsule-v2 -->
# Agent-facing state injection — how does the LLM learn about workflows, the op log, and browser rules without a tool call?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do live operational state (workflow statuses, dedup history) and hard safety rules get into the system prompt, and what keeps an agent from destroying its own login session?

## Exec-sourced dynamic sections + the Browser Connection Contract
**Path/Symbol:** `src/constants/prompts.ts`:`getWorkflowStatusSection` (`:312-353`), `getOperationLogSection` (`:290-310`), `getBrowserConnectionSection` (`:355-423`), `getAgentBrowserSection` (`:425+`).
**Signature:** Each is a zero-arg function returning `string` (empty when its backing script/log is absent) executed while assembling the system prompt; each shells out with `execFileSync(process.execPath, ['run', script, ...], { timeout: 5000 })`.
**Data Shape:** Workflow section = engine `summary` output (status/runCount/lastRun per workflow + control-command cheatsheet); op-log section = 30-day success counts + already-acted URL lists wrapped in "Do NOT repeat any action on a URL already listed".

### Decisive source
```ts
// Feature-detect the fork layer — upstream clones without it get nothing:
if (!existsSync(join(__dirname, '../../scripts/setup-chrome.ts'))) return ''
...
return [
  `# Browser Connection Contract (READ BEFORE ANY BROWSER ACTION)`,
  ``,
  `All social-media automation runs against ONE dedicated browser: an isolated,`,
  `persistent Chrome with CDP enabled on port 9222, launched by \`bun run setup-chrome\`.`,
  ...
  `- **NEVER attempt an automated login.** ... This is the single worst`,
  `  failure mode — avoid it absolutely.`,
  `- **If the isolated profile is logged out, STOP and ask the user.**`,
  ...
].join('\n')
```

**Flow:** at prompt build time, run the engine's `summary` (5 s timeout, failure ⇒ empty section, never a crashed prompt) → inject it with a control-cheatsheet so the agent can start/stop/inspect workflows via Bash → inject the op-log summary with the check-before-acting rule → detect the fork by probing for `setup-chrome.ts` on disk, and only then inject the full contract: one dedicated CDP browser, pin explanation ("that error means run setup-chrome, NOT a login problem"), preflight ladder (doctor --check-cdp → setup-chrome → snapshot to confirm login), and the hard rules.
**Invariant:** The three worst failure modes are forbidden explicitly and non-negotiably: automated login attempts (rate-limit/flag risk), spinning up fresh sessions/profiles (no cookies → drags into login flow), and killing/closing the browser to "fix" login (destroys the session). A logged-out profile routes to "STOP and ask the human", never improvisation. Sections degrade to empty strings on any error — state injection must not be able to break prompt assembly.
**Probe:** No direct test for prompts.ts (coverage caveat — source-grounded). Deterministic probe: `search_graph --project locoagent --query "Browser Connection Contract"` / grep pins the section text at `src/constants/prompts.ts:367-423`; the same rules are restated in `skills/x-com/SKILL.md`, showing the intended redundancy.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getWorkflowStatusSection getOperationLogSection browser connection", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt exec-with-timeout state sections that fail soft, fork feature-detection before injecting fork-specific rules, and the explicit hard-rule list (no auto-login, no fresh-session escape hatch, stop-and-ask on logout). Adapt ports, commands, and wording. Omit nothing from the hard rules when porting agentic browser operation — they encode real account-ban incident history.
