<!-- capsule-v2 -->
# Local-server install consent — what must a client do before running a one-click local MCP server install?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e`; Codebase Memory `modelcontextprotocol`. **Question:** When an MCP client offers one-click installation of a LOCAL (command-launched) server, what security controls are mandatory before it executes the install command?

## Pre-configuration consent (SEP-1024, Final)
**Path/Symbol:** `seps/1024-mcp-client-security-requirements-for-local-server-.md` (whole; Abstract :11–13; attack vectors :17–27; normative controls :35–49; residual risks :88–100).

**Data Shape:** this is a CLIENT-side behavioral requirement, not a wire-format change. It applies to any client that supports one-click configuration of a local MCP server (i.e. a server launched by executing a command on the user's machine). The threat model is silent/arbitrary command execution via crafted server configs distributed through links, repos, docs, or social engineering.

### Decisive source
```text
// seps/1024-...md:39-49 (normative controls)
Before executing any command to install or configure a local MCP server, the MCP client **MUST**:
1. Display a clear consent dialog that shows:
   - The exact command that will be executed, without truncation
   - All arguments and parameters
   - A clear warning that this operation may be potentially dangerous
2. Require explicit user approval through an affirmative action (button click, checkbox, etc.)
3. Provide an option for users to cancel the installation
4. Not proceed with installation if consent is denied or not provided
```

**Flow:** user triggers one-click add of a local server → client renders a consent dialog showing the EXACT command (untruncated) + every argument + a "potentially dangerous" warning → user takes an affirmative action (or cancels) → only on explicit approval does the client execute the command; on denial/absence it aborts.

**Invariant:** no local-server install command may execute without (a) full command transparency (exact command, untruncated, all args), (b) an explicit affirmative opt-in, and (c) a cancel path; denial or no-response MUST block execution. The protocol/wire format is unchanged — this is purely a client duty.

**Residual risks (honest):** user override (approving a malicious command), sophisticated obfuscation, and implementation gaps remain; mitigations are clear warning language plus recommended extra layers (sandboxing, signatures).

**Probe (deterministic, graph not connected this pass):** `grep -n "without truncation\|affirmative action\|cancel the installation" seps/1024-*.md` ⇒ lines 42/45/47 at pin 57ac4a2e. No runtime test in the spec repo (client behavior is out of scope of the spec repo's CI); the SEP text is the machine-checkable anchor.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "Pre.Configuration.Consent|one.click.local.MCP.server|exact.command.without.truncation|affirmative.action", limit: 10 });
```

## Verdict
Adopt for any client with a one-click local-server install flow: gate every install command behind a consent dialog that shows the exact untruncated command + all arguments + a danger warning, require an explicit affirmative action, offer cancel, and hard-abort on denial or no response. Adapt the dialog UX to your host; omit nothing from the four MUSTs. This is a client-security duty independent of the wire protocol.
