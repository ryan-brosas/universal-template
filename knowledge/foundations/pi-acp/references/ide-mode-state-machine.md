<!-- capsule-v2 -->
# IDE coding mode state machine — how does an adapter enforce "the IDE applies all code" without breaking when its tools vanish mid-session?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you gate an external agent's file mutations on a remote IDE toolset whose availability is only known after an async catalog handshake, and degrade/fail-closed without deadlocking the host extension runtime?

## IDE mode FSM over async catalog arrival
**Path/Symbol:** `src/pi-extension/acp-mcp-bridge.ts` (`activateAcpMcpBridgeExtension` :440, `transitionIdeState` :840-863, `applyIdePolicy` :865-891, `parseIdeCodingMode` :1108-1113, `indexIdeCapabilities` :1115-1145, `evaluateIdeAvailability` :1147-1154).
**Signature:** `function parseIdeCodingMode(value: string | undefined): { mode: 'off'|'prefer'|'required'; diagnostic?: string }`; `function evaluateIdeAvailability(mode: IdeCodingMode, capabilities: IdeCapabilityMap): { state: IdeCodingState; missing: IdeCapabilityKey[] }`.
**Data Shape:** `PI_ACP_IDE_MODE ∈ {'off','prefer','required'}`; ANY OTHER VALUE FAILS CLOSED TO `'required'` with a diagnostic (`invalid PI_ACP_IDE_MODE value '%s'; failing closed as required`). States: `disabled → awaiting_catalog → active | native_fallback | required_unavailable → shutdown`. Capability map keys `read|open|patch|create|search|inspect` (required) and `rename|reformat` (optional), each resolved by FIRST matching remoteName from an ordered candidate list (`read_file`, `open_file_in_editor`, `apply_patch`, `create_new_file`, `skill_search|search_text`, `lint_files|get_file_problems`) among REGISTERED exposed names only.

### Decisive source
```ts
export function parseIdeCodingMode(value: string | undefined): { mode: IdeCodingMode; diagnostic?: string } {
  if (value === undefined || value === '' || value === 'off') return { mode: 'off' }
  if (value === 'prefer') return { mode: 'prefer' }
  if (value === 'required') return { mode: 'required' }
  return { mode: 'required', diagnostic: `invalid PI_ACP_IDE_MODE value '${value}'; failing closed as required` }
}
```

**Flow:** env parsed once at activation → if not off, `before_agent_start` hook appends `renderIdeCodingGuidance(mode,state,capabilities,projectRoot)` (+ accumulated policyDiagnostics) to the system prompt → `hello_ack` triggers `registerTools` then `applyIdePolicy`: missing project root ⇒ fallback state; else capability indexing (duplicates recorded as diagnostics) → `evaluateIdeAvailability`: all required present ⇒ `active` (removes native tools read/edit/write/grep/find/ls from pi active set AND activates IDE tools); missing under `prefer` ⇒ `native_fallback` (IDE tools deactivated, ONLY native tools removed BY THIS POLICY restored — tracked in `removedByPolicy` so a foreign removal is never undone); missing under `required` ⇒ `required_unavailable` (task blocked until fresh session). IPC disconnect maps prefer→`native_fallback`, required→`required_unavailable`.
**Invariant:** every tool-set mutation goes through `schedulePolicyWhenReady` retry: pi throws `Extension runtime not initialized` for action methods while extensions are still loading (a nested pi can inherit live IPC env), so the handler catches that exact error class (`RUNTIME_NOT_READY_RE = /runtime not initialized|during extension loading/i`) and defers via `setImmediate`, capped at `MAX_DEFERRED_POLICY_ATTEMPTS = 500`. A second bridge instance in one process is impossible: `claimBridgeInstance(scope, owner)` guards a `Symbol.for('pi-acp-jetbrain.acp-mcp-bridge.instance')` registry slot, released on `session_shutdown` or failed connect.
**Probe:** `npx tsx --test test/unit/acp-mcp-extension.test.ts` (runtime-not-ready deferral, singleton claim/release, guidance rendering, invalid-mode fail-closed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "transitionIdeState applyIdePolicy evaluateIdeAvailability", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tri-state fail-closed mode parse, the capability-index-then-evaluate ordering, the policy-owned restore ledger for native tools, and the runtime-not-ready defer-with-cap pattern. Adapt the specific remote names/capability groups and the system-prompt guidance wording to your IDE's tool surface. Omit the JetBrains-specific tool descriptions. Direct tests exist and were executed green at the pin.
