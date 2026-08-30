<!-- capsule-v2 -->
# Bridge registration health frame — how should a bridge extension report per-tool registration outcomes so partial catalogs are visible instead of silently degraded?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How should a bridge extension report per-tool registration outcomes back to the adapter so a partially-registered catalog is visible instead of silently degraded?

## Registration ledger + health frame
**Path/Symbol:** `src/pi-extension/acp-mcp-bridge.ts` — `registerTools` :522-564, `handleMessage` hello_ack branch :566-604 (health send :592-600), `CatalogRegistration` shape (src/acp/mcp-types.ts).
**Signature:** `function registerTools(tools: BridgeTool[]): CatalogRegistration` — returns `{catalogId, registered: [{exposedName, schemaHash}], failed: [{exposedName, schemaHash, message}], diagnostics?}`.
**Data Shape:** health frame `{ type: 'health', health: { state: 'registration_complete' | 'registration_partial', catalogId, diagnostics: string[] } }`; per-tool failure entries carry the tool's `schemaHash` so the adapter can correlate against its own catalog expectations.

### Decisive source
```ts
// registerTools: duplicate exposed names and registration throws BOTH land in the failed
// ledger — never thrown out of the loop — and schema-conversion warnings attach per tool
if (names.has(tool.exposedName)) {
  registration.failed.push({ exposedName: tool.exposedName, schemaHash: tool.schemaHash,
    message: 'duplicate exposed tool name' })
  continue
}
...
if (conversionState.warnings.length > 0)
  registration.diagnostics = [...(registration.diagnostics ?? []),
    `${tool.exposedName}: ${conversionState.warnings.join('; ')}`]
} catch (error) {
  registration.failed.push({ exposedName: tool.exposedName, schemaHash: tool.schemaHash,
    message: error instanceof Error ? error.message : String(error) })
}
// hello_ack branch: catalog_registered FIRST, then the health frame whose state is derived
// from the ledger — the adapter learns the outcome twice: structured entries + a state flag
send({ type: 'catalog_registered', registration })
send({ type: 'health', health: {
  state: registration.failed.length === 0 ? 'registration_complete' : 'registration_partial',
  catalogId: msg.catalog.catalogId,
  diagnostics: [...(registration.diagnostics ?? []),
    ...registration.failed.map(item => `${item.exposedName}: ${item.message}`)]
} })
```

**Flow:** `hello_ack` arrives → `registerTools` walks the catalog: duplicate exposed names short-circuit into `failed`; each `pi.registerTool` call is individually try/caught so one bad tool (schema conversion throw, host rejection) cannot abort the batch; schema-conversion warnings (widened constructs from `schemaToTypeBox`) attach as per-tool diagnostics. The registration (with `catalogId` backfilled) goes to the adapter as `catalog_registered`; a SECOND frame, `health`, carries the derived state — `registration_complete` only when `failed` is empty, else `registration_partial` — plus flattened diagnostics. The adapter's `validateCatalogRegistration` (mcp-ipc side, owned by mcp-bridge-ipc.md) independently rejects mismatches; this frame is the extension-side confession that complements it.
**Invariant:** registration of N tools is all-or-nothing per tool but never per batch — a batch with any failure still registers the healthy remainder AND reports the shortfall; the health state is DERIVED from the ledger (`failed.length === 0`), never asserted, so the two frames cannot disagree; diagnostics are flattened into the health frame so a consumer reading only `health` still sees every failure.
**Probe:** `test/unit/acp-mcp-extension.test.ts` (1212L, ~80 tests; decisive ranges read this pass) — the lifecycle describe block drives a fake socket through `hello_ack` and asserts the emitted `catalog_registered` frame incl. diagnostics (:491); the singleton/deferral tests (:1191-1212) pin the surrounding activation contract. The health frame itself is source-read only at this pin (no test asserts `registration_partial` directly) — recorded as a coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "registerTools CatalogRegistration registration_complete health frame", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-tool try/caught registration ledger with schemaHash correlation, the derived-state health frame sent alongside the structured registration, and diagnostics flattening. Adapt the frame vocabulary to your IPC protocol. Omit the dual-frame split if your adapter consumes the registration object directly. Coverage caveat: `registration_partial` branch is source-read only at this pin.
