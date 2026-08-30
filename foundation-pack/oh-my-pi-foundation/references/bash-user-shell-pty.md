<!-- capsule-v2 -->
# User-shell PTY execution — when must a bash tool run the user's interactive shell on a real PTY, and how do you keep the model's transcript clean while doing it?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What is the full eligibility ladder for the interactive PTY path, and what env/capture transformations does it require that a naive port gets wrong?

## Interactive PTY eligibility + capture split
**Path/Symbol:** `packages/coding-agent/src/exec/bash-executor.ts:` gate in `executeBash` (:443–451), `executeUserShellPty` (:376–430), `buildUserShellPtyEnv` (:359–367); UI-capability predicate `src/tools/bash-pty-selection.ts canUseInteractiveBashPty` (:10–14).
**Signature:** `canUseInteractiveBashPty(pty: boolean, ctx: BashPtyContext | undefined): boolean; async function executeUserShellPty(run: {shell; args; command; cwd; env; pty: BashPtyOptions; timeoutMs?; signal?; sink}): Promise<BashResult>`.
**Data Shape:** `BashPtyOptions {cols, rows, onChunk(rawBytes)}` — raw PTY bytes (ANSI intact) stream to the virtual terminal renderer; `OutputSink` keeps a separate SANITIZED capture (ANSI stripped) for transcript + model.

### Decisive source
```ts
const usePty =
	ptyRequest !== undefined &&
	options?.useUserShell === true &&
	!bashShell &&                    // bash keeps the snapshot + embedded-shell path
	supportsAutoUserShell(shell) &&  // zsh/fish only
	$env.PI_NO_PTY !== "1" &&        // env kill-switch
	!isPersistentShellCdCommand(command); // cd keeps the persistent shell so session cwd follows
```
```ts
function buildUserShellPtyEnv(shellEnv, commandEnv): Record<string, string> {
	// Keep non-interactive guards (pagers, editors, credential prompts) but
	// restore color — the PTY makes stdout a TTY, so TERM/NO_COLOR/CI are all
	// that keep tools monochrome.
	const env = { ...shellEnv, ...commandEnv, TERM: "xterm-256color" };
	delete env.NO_COLOR;
	delete env.CI;
	return env;
}
```

**Flow:** `!` hotkey command → eligibility ladder above → eligible ⇒ `new PtySession().startArgv({application: user shell, args:[...interactiveArgs, command], cols, rows}, cb)` where cb routes raw chunks to `pty.onChunk` (renderer) and CRLF→LF-folded text into the sink (ANSI stripped later); timeout/cancelled produce `exitCode: undefined` results with dumped sanitized output. Ineligible ⇒ legacy embedded-shell path with chunk throttling (`chunkThrottleMs ?? 50`).
**Invariant:** Two output planes must never be conflated: the RENDERER consumes raw ANSI bytes at viewport size; the MODEL sees the sanitized LF-folded capture. Env must delete NO_COLOR and CI but KEEP pagers/editors guards — restoring color without re-enabling interactive editors is the whole trick. The kill switch is checked in BOTH layers (`canUseInteractiveBashPty` for tool-call gating, `$env.PI_NO_PTY` again inside executeBash).
**Probe:** `test/tools/bash-pty-selection.test.ts` pins the predicate cross-platform (`"allows interactive PTY on Windows when requested with UI"`, `"allows interactive PTY on non-Windows when requested with UI and not disabled"`); env transform verified byte-exact at pin: `grep -c 'delete env.NO_COLOR;' src/exec/bash-executor.ts` → 1 (executed green).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "canUseInteractiveBashPty executeUserShellPty PtySession user shell", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `executeUserShellPty bash-executor.ts:376-430`, `canUseInteractiveBashPty bash-pty-selection.ts:10-14`.

## Verdict
Adopt the six-clause eligibility ladder, dual output planes, and color-restoring env surgery. Adapt PtySession to your host's PTY primitive. Omit the zle/gitstatus rationale details beyond what drives the design (they explain WHY, not WHAT to port).
