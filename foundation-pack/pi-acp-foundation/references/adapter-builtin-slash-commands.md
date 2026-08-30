<!-- capsule-v2 -->
# Adapter-side built-in slash commands — which commands must an adapter intercept before the agent sees them?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you implement a "headless-friendly" command subset that answers instantly with zero model calls, and what preconditions must be guarded when an agent RPC can fail uncorrelated?

## Builtin dispatch inside prompt()
**Path/Symbol:** `src/acp/agent.ts:PiAcpAgent.prompt` (:571-~1040) — dispatch cases `compact` (:585), `session` (:612), `name` (:647), `steering` (:698), `follow-up` (:745), `changelog` (:792, incl. `findChangelog` :794-830), `export` (:873), `autocompact` (:992); table source `builtinAvailableCommands` (:94-134). Direct tests: `test/unit/builtin-commands.test.ts`, `test/component/agent-steering-followup-modes.test.ts`.
**Signature:** inside `prompt(params: PromptRequest)` — gate `images.length === 0 && message.trimStart().startsWith('/')`, then first-token command match; every branch returns `{ stopReason: 'end_turn' }`.
**Data Shape:** Args parsed once via `parseCommandArgs`; replies are `agent_message_chunk` text updates (or `session_info_update` title + `resource_link` for export); nothing is forwarded to pi for matched commands (`proc.prompts.length === 0` pinned).

### Decisive source
```ts
// Built-in ACP slash command handling (headless-friendly subset).
// Note: file-based slash commands are expanded inside session.prompt().
if (images.length === 0 && message.trimStart().startsWith('/')) {
  const trimmed = message.trim()
  const space = trimmed.indexOf(' ')
  const cmd = space === -1 ? trimmed.slice(1) : trimmed.slice(1, space)
  const argsString = space === -1 ? '' : trimmed.slice(space + 1)
  const args = parseCommandArgs(argsString)

  if (cmd === 'compact') { /* proc.compact(customInstructions) -> header lines + summary chunk */ }
  if (cmd === 'session') {
    const stats = (await session.proc.getSessionStats()) as any
    ...
    // Fallback if stats shape changes.
    const text = lines.length ? lines.join('\n') : `Session stats:\n${JSON.stringify(stats, null, 2)}`
```
```ts
if (cmd === 'export') {
  // IMPORTANT: Pi's `export_html` reads the session JSON Lines file. If it doesn't exist yet
  // (no messages) or is empty, pi throws and RPC mode emits an uncorrelated parse error
  // (no id), which would otherwise hang our request. So we guard here.
  if (!sessionFile || messageCount === 0 || !existsSync(sessionFile)) { /* usage chunk; end_turn */ }
  const safeSessionId = session.sessionId.replace(/[^a-zA-Z0-9_-]/g, '_')
  const outputPath = join(session.cwd, `pi-session-${safeSessionId}.html`)
  ... // error + empty-resultPath fallbacks, then prefix-text chunk + resource_link chunk
}
```

**Flow:** prompt arrives → image-free leading-slash gate → split command/args → per-command handler: read-or-set pattern for steering/follow-up/autocompact (report current on empty arg, validate enum, set via RPC, confirm); stats/name/changelog/export produce formatted chunks — `/name` additionally emits `session_info_update {title}` (and enriches failures of old pi versions with a `set_session_name` hint); `/changelog` locates the installed pi package via `which`+realpath (two dirs up from bin) or `npm root -g` fallback and caps output at 20k chars; `/export` sanitizes the session id into the filename and emits link + prefix separately because clients concatenate chunks.
**Invariant:** Matched commands NEVER reach the model or pi's prompt loop; every branch terminates the turn with `end_turn` after emitting at least one user-visible chunk (usage errors included); RPCs known to emit uncorrelated (id-less) parse errors must have their preconditions checked adapter-side BEFORE the call.
**Probe:** `test/unit/builtin-commands.test.ts` ("/steering is handled adapter-side" pins `stopReason==='end_turn'` AND `proc.prompts.length===0` AND reply `/Steering mode: one-at-a-time/`; "/name sets session display name adapter-side" pins setSessionName call + `session_info_update.title`) + `test/component/agent-steering-followup-modes.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "steering follow-up changelog export autocompact adapter handled stopReason end_turn", limit: 10 });
// -> PiRpcProcess.setSteeringMode/setFollowUpMode/exportHtml src/pi-rpc/process.ts; test/component/agent-steering-followup-modes.test.ts
```

## Verdict
Adopt the interception gate (no images + leading slash), terminate-every-branch-with-end_turn contract, report-on-empty-arg UX, precondition guards before id-less-error-prone RPCs, and chunk-concatenation-aware link emission. Adapt the command set and stat formatting to your agent; keep the "adapter answers without a model call" property. Omit the changelog npm-locator heuristics unless your host ships a global CLI too.
