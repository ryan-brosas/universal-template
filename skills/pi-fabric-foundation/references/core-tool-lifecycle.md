<!-- capsule-v2 -->
# Tool ownership & lifecycle — who owns the active tool set, and how does a wrapper tool's failure propagate to its outer tool_result?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how do you swap the model-visible active tool set (hide natives + captured tools, add one facade tool) with exact restore, and how does a nested call inside the facade mark the OUTER result as error?

## Active-set ownership with index-faithful restore
**Path/Symbol:** `src/core/tool-ownership.ts:FabricToolOwnership.apply` (:148-174), `#restore` (:180-194), `createToolOwnershipReassertion` (:116-136); `FabricToolLifecycle` (:47-101); `ownsFabricToolSource` (:28-35).
**Signature:** `apply(fullCodeMode: boolean, hiddenExtensionTools?: ReadonlySet<string>): boolean`; `createToolOwnershipReassertion({ready, active, hiddenNames, apply}): {reassert(): void; schedule(): void}`; `FabricToolLifecycle.toolCall(event, context?): Promise<ToolCallEventResult | undefined>` / `.toolResult(event): {isError: true} | undefined`.
**Data Shape:** saved state = `{#savedNativeCoreTools: Array<{name, index}> | undefined, #savedHiddenExtensionTools: Map<name, index>}`; lifecycle tracks `#outerCalls: Set<toolCallId>` of in-flight owned facade calls.

### Decisive source
```ts
apply(fullCodeMode, hidden) {
  const active = this.host.getActiveTools();
  if (!fullCodeMode) return this.#restore(active);
  this.#savedNativeCoreTools ??= active.flatMap((name, i) =>
    PI_CORE_TOOL_NAME_SET.has(name) ? [{ name, index: i }] : []);   // first-seen snapshot
  ...
  for (const [name, index] of this.#savedHiddenExtensionTools) {    // re-hide after refresh
    if (hidden.has(name) || next.includes(name)) continue;
    this.#savedHiddenExtensionTools.delete(name);
    next.splice(Math.min(index, next.length), 0, name);             // re-insert at SAVED slot
  }
  if (!next.includes("fabric_exec")) next.push("fabric_exec");
  return this.#setIfChanged(active, next);                          // no-op when identical
}
// Re-assertion is microtask-deduped and readiness-gated:
schedule: () => { if (queued) return; queued = true; queueMicrotask(reassert); }
reassert = () => { queued = false;
  if (!options.ready() || !options.active()) return;   // registry rebuilds precede session_start
  options.apply(options.hiddenNames()); };
```
```ts
// Failure laundering: an owned outer call whose trace details report
// success===false or trace.outcome !== "succeeded" becomes isError on the way out:
return !event.isError && finalFabricDetailsFailed(event.details)
  ? { isError: true } : undefined;
```

**Flow:** enter full-code mode → snapshot native core tools ONCE at their live indices, drop them, drop hidden captured tools (recording each one's index), append the facade → host refreshes re-run `schedule()` (deduped microtask, gated on `ready()`) which re-hides re-enabled tools and restores unhidden ones at their saved slots → leaving full mode restores both saved groups by original index. During a facade invocation its id sits in `#outerCalls`; nested generated ids are allowed only then; every other top-level tool call passes authorize/approve gates.
**Invariant:** restore must be index-faithful (`splice(min(index, len))`) so tools land where the host put them originally; ownership writes are skipped entirely when the set already matches (`sameTools` guard). A nested failure never surfaces as an error on the nested result — it is laundered onto the outer fabric_exec result exactly once (outer ids only, delete-on-sight).
**Probe:** `tests/tool-ownership.test.ts:23` ("exclusive ownership of active Pi core tools"), `:85` ("rehides extension tools that a refresh re-activated"), `:106` (restore on release), `:121` ("no-ops scheduled reassertions that run before the host is ready"); `tests/tool-lifecycle.test.ts:122` ("does not mark a valid succeeded trace as an error"), `:275` ("allows generated nested ids only during an owned outer invocation").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "FabricToolOwnership apply restore active tools FabricToolLifecycle toolCall toolResult isError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt index-snapshotted active-set swapping with microtask-deduped, readiness-gated re-assertion, and outer-result failure laundering keyed on structured details (not prose); adapt the core/native tool-name set and the single-facade assumption; omit the pi event types. Caveat: `ownsFabricToolSource` resolves provenance from source paths — SDK/extension metadata claims are deliberately ignored.
