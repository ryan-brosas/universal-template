<!-- capsule-v2 -->
# Direct-tool approval bridge — how do Pi core/extension tools enter Fabric's risk ladder without re-wrapping the tools?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for applying fabric approvals + auto-approval classification to tools Fabric did NOT capture?

## Connected graph-selected seam
**Path/Symbol:** `src/core/direct-tool-approval.ts` — `FabricDirectToolApproval.approve` (:62-76), `#resolve` (:88-100), `mergeFabricApprovalUsage` (:43-46), `takeUsage` (:78-82).
**Signature:** `approve(event: ToolCallEvent, context)` → runs a FRESH `ApprovalController` per event (config + sessionApprovals + classifier read at call time); `takeUsage(toolCallId)` consumes-and-deletes pending classifier usage.
**Data Shape:** synthesized `ResolvedFabricAction` `{ ref: "pi.<tool>" | "extensions.<tool>", provider, name, description, inputSchema, risk }` — provider is derived from `metadata.sourceInfo.source === "builtin"`, never from a registry.

### Decisive source
```ts
  #resolve(toolName: string, config: FabricConfig): ResolvedFabricAction {
    const metadata = this.pi.getAllTools().find((tool) => tool.name === toolName);
    const builtin = metadata?.sourceInfo.source === "builtin";
    const provider = builtin ? "pi" : "extensions";
    return {
      ref: provider + "." + toolName,
      ...
      inputSchema: isRecord(metadata?.parameters) ? metadata.parameters : {},
      risk: config.capture.risks[toolName] ?? config.capture.defaultRisk,
    };
  }
```

**Flow:** on every direct (non-captured) tool call, resolve a synthetic action → construct ApprovalController with the SAME session approvals/classifier the captured path uses → approve; auto-approvals fire `onAutoDecision`, which both forwards the audit AND stashes the classifier's token usage under the toolCallId — the host later drains it via `takeUsage` and folds it into native usage with `mergeFabricApprovalUsage` (field-wise sum; optional fields `cacheWrite1h`/`reasoning` present iff EITHER side has them, `?? 0` coalescing). `clear()` wipes pending usage on teardown.
**Invariant:** NO tool wrapping — the same tool instance keeps executing; only the approval gate is bridged. Risk comes from explicit per-tool config else the default; unknown tools still classify as `extensions.*` rather than bypassing approval; classifier usage must be consumed exactly once (`Map.delete` semantics) or it would double-count.
**Probe:** `tests/direct-tool-approval.test.ts:53` ("applies configured core and extension risks without wrapping their tools"), `:74` ("classifies auto calls with the native action and retains classifier usage"), `:125` ("adds classifier usage to existing native tool usage").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "FabricDirectToolApproval mergeFabricApprovalUsage takeUsage sourceInfo builtin", limit: 5, fields: ["signature", "name", "file"] });
```
