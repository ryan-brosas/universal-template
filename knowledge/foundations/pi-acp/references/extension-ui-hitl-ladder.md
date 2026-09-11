<!-- capsule-v2 -->
# Extension UI requests — pi select/confirm laddered onto ACP request_permission

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does an ACP adapter surface host-extension UI prompts (select/confirm/input/editor/notify) to a client that only knows ACP's `session/request_permission`, and what must be answered when the client cancels?

## HITL ladder
**Path/Symbol:** `src/acp/session.ts` — dispatch case `extension_ui_request` (:860-873), `handleExtensionUiRequest` (:960-1001), `handleExtensionSelect` (:1002-1026), `handleExtensionConfirm` (:1027-1039), `requestExtensionPermission` (:1041-1058), `extensionUiToolCall` (:1059-1076), `optionIndex` (:1082-1095); constants :59-64.
**Signature:** `handleExtensionUiRequest(ev: PiRpcEvent): Promise<void>`; `requestExtensionPermission(id, ev, options): Promise<PermissionResponse | null>`.
**Data Shape:** pi event carries `id`, `method` (`select|confirm|input|editor|notify`), plus raw keys. Constants: `CONFIRM_PERMISSION_OPTIONS = [{optionId:'yes',name:'Yes',kind:'allow_once'},{optionId:'no',name:'No',kind:'reject_once'}]`; `EXTENSION_UI_RAW_INPUT_KEYS = ['title','message','options','placeholder','prefill']`; `CHOICE_OPTION_PREFIX = 'choice-'`.

### Decisive source
```ts
// select: N string options → N synthetic allow_once permission options
const permissionOptions = options.map((name, index) => ({
  optionId: `${CHOICE_OPTION_PREFIX}${index}`,   // 'choice-0', 'choice-1', ...
  name,
  kind: 'allow_once'
}))
const selected = await this.requestExtensionPermission(id, ev, permissionOptions)
if (selected === null) return                   // permission call threw; response already sent cancelled
const selectedOptionId = selected.outcome.outcome === 'selected' ? selected.outcome.optionId : null
const index = selectedOptionId === null ? null : optionIndex(selectedOptionId)
const value = index === null ? null : (options.at(index) ?? null)
await this.proc.sendExtensionUiResponse(value === null ? { id, cancelled: true } : { id, value })
```
```ts
// confirm: fixed yes/no pair → boolean
if (selected.outcome.outcome === 'cancelled') await this.proc.sendExtensionUiResponse({ id, cancelled: true })
else await this.proc.sendExtensionUiResponse({ id, confirmed: selected.outcome.optionId === 'yes' })

// input/editor/notify/unknown: NEVER hang the extension — cancel with a visible marker
this.emit({ sessionUpdate: 'agent_message_chunk',
  content: { type: 'text', text: `Pi ${method} UI request is not supported in ACP yet; cancelling it.` } })
await this.proc.sendExtensionUiResponse({ id, cancelled: true })
```

**Flow:** dispatch is fire-and-forget (`void handleExtensionUiRequest(ev).catch(...)`); ANY rejection inside the handler sends `{id, cancelled:true}` best-effort so the pi-side extension never awaits forever. `select` maps each option string to a synthetic `PermissionOption` and back through a strict index codec (`optionIndex`: prefix check, safe integer, canonical decimal round-trip `String(index) === rawIndex`). `confirm` uses the fixed yes/no pair where `optionId === 'yes'` IS the boolean. The prompt is rendered by reusing the tool-call surface: `extensionUiToolCall` builds `toolCallId: 'pi-ui-<id>'`, `kind:'other'`, `status:'pending'`, `rawInput` = whitelisted raw keys + method.

**Invariant:** every branch terminates in exactly one `sendExtensionUiResponse` — `value` for a real selection, `confirmed:<bool>` for confirm, `cancelled:true` for cancel/unsupported/error/empty-options. A porter who forgets the empty-options or cancelled-outcome branches deadlocks the pi extension awaiting a reply that never comes. Cancelled permission outcome ≠ selection of "no": confirm distinguishes them (`cancelled` vs `confirmed:false`).

**Probe:** `test/component/session-events.test.ts` — "handles extension select via ACP permission request" (:149, `nextPermissionResponse choice-1`), "handles extension confirm" (:191, pins `confirmed:false` from optionId 'no'), "sends cancelled response when ACP confirm is cancelled" (:223), "cancels unsupported input and editor ... with visible fallback" (:243, asserts BOTH the cancelled responses and the visible text).
**Coverage:** session.ts `partial` at :36 only (read directly); all ranges above verified in source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "handleExtensionUiRequest requestPermission sendExtensionUiResponse CONFIRM_PERMISSION_OPTIONS", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the method ladder (select→indexed choices, confirm→boolean, everything else→cancel-with-marker), the single-response termination invariant, and the strict optionId↔index codec. Adapt option kinds/labels to your client's permission vocabulary. Omit nothing else — the ladder is the whole contract. **DRIFT UPDATE (pass 3, `1f0524f`):** the `input` arm NO LONGER auto-cancels — it now opens a real ACP form elicitation (`unstable_createElicitation`, single string field from title/placeholder, 300s default timeout, non-accept/throw ⇒ visible-cancel fallback); `editor` keeps its own dedicated marker ("no multiline elicitation form"). Full detail: elicitation-input-slash-args.md.
