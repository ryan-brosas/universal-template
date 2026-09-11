<!-- capsule-v2 -->
# Elicitation input upgrade + slash-command arg algebra — how does an adapter turn unsupported extension UI into real form elicitation, and which substitution order keeps prompt args single-pass?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you map a free-text extension UI request onto ACP's unstable elicitation API with timeout fallback, and what is the exact argument-substitution grammar that must stay one-pass?

## handleExtensionInput (form elicitation) + substituteArgs grammar
**Path/Symbol:** `src/acp/session.ts` (`handleExtensionInput` :1089-1134, editor branch split :1020-1035) + `src/acp/slash-commands.ts` (`substituteArgs` :190-222, `withFileCommandInputs` :141-155). (Elicitation call sites: `unstable_createElicitation` :1099 in `handleExtensionInput`; editor branch cancels with no multiline form.)
**Signature:** `private async handleExtensionInput(ev: PiRpcEvent, id: string): Promise<void>`; `export function substituteArgs(content: string, args: string[]): string`; `export function withFileCommandInputs(commands: AvailableCommand[], fileCommands: FileSlashCommand[]): AvailableCommand[]`.
**Data Shape:** elicitation = `unstable_createElicitation({ mode:'form', sessionId, message: title, requestedSchema: { type:'object', title, properties:{ value:{ type:'string', description?: placeholder } }, required:['value'] } })`; default UI timeout 300_000ms (event `timeout` honored when positive); pi response `{id, value}` or `{id, cancelled:true}`.

### Decisive source
```ts
const response = await withTimeout(this.conn.unstable_createElicitation({...}), timeout)
if (response.action !== 'accept' || typeof response.content?.value !== 'string') {
  await this.proc.sendExtensionUiResponse({ id, cancelled: true }); return
}
await this.proc.sendExtensionUiResponse({ id, value: response.content.value })
} catch {
  // client lacks UNSTABLE elicitation (or call failed): visible cancellation so pi never hangs
```

**Flow:** `input` requests now open a REAL single-field form instead of auto-cancelling; non-accept/missing-string → cancelled; ANY throw → visible agent_message_chunk marker + cancelled (the never-hang invariant from the HITL ladder preserved). `editor` split out of the shared arm with its own precise marker ('no multiline elicitation form'). Command metadata gains input hints via `withFileCommandInputs` — first file-command hint per name wins, existing `input` NEVER overwritten, ORDER of commands untouched. `substituteArgs` stays ONE regex pass over `${N|ARGUMENTS|@}:-default`, `${@:start(:len)}` slices (1-based), and bare `$N|$@|$ARGUMENTS` — inserted values are never rescanned.
**Invariant:** exactly one extension_ui_response per request id (single-response termination); substitution is single-pass so user text containing `$1` cannot expand; hints enrich without reordering — merge precedence remains builtin > pi-RPC > file commands.
**Probe:** `npx tsx --test test/unit/slash-commands.test.ts` (substitution grammar matrix incl. slices/defaults/quote parsing; executed GREEN at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "handleExtensionInput substituteArgs withFileCommandInputs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt elicitation-with-timeout-fallback for free-text UI and the single-pass three-form substitution grammar. Adapt schema shape to your client's elicitation support surface. Omit the editor branch if your host has multiline forms. Direct tests executed green at pin (elicitation path covered by session tests at HEAD; substitution fully pinned).
