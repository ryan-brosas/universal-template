<!-- capsule-v2 -->
# Nested tool result middleware — how do extension result-patchers see a nested tool_result without corrupting the value the provider returned?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how do you route a nested (facade-executed) tool result through host `tool_result` middleware and decide what the real return value is?

## Proxy-details round trip with identity comparison
**Path/Symbol:** `src/core/tool-result-proxy.ts:FabricToolResultProxy.proxy` (:52-91); protocol reader `readFabricToolResultProxyDetailsV1` in `src/protocol.ts`; settlement helper `runAbortable` in `src/async-settlement.ts:35-45`.
**Signature:** `proxy(request: {action: ResolvedFabricAction; args: Record<string, unknown>; toolCallId: string; value: unknown; signal?: AbortSignal}): Promise<unknown>`.
**Data Shape:** emitted details = `{kind: FABRIC_TOOL_RESULT_PROXY_KIND, ref, result}` (namespaced v1 envelope); middleware patch = `{content?, details?, isError?}`.

### Decisive source
```ts
if (nativeLifecycleProviders.has(request.action.provider)) return request.value; // pi/extensions already emit
...
const patch = await runAbortable(request.signal, () => runner.emitToolResult({
  type: "tool_result", toolName: request.action.ref, toolCallId: request.toolCallId,
  input: request.args, content, details, isError: false }));
if (!patch) return request.value;
const patchedContent = patch.content ?? content;
if (patch.isError === true)                       // middleware veto => invocation failure
  throw new Error(textFromContent(patchedContent).trim() ||
    `Fabric result middleware marked ${request.action.ref} as failed.`);
const patchedDetails = readFabricToolResultProxyDetailsV1(patch.details);
if (patchedDetails?.ref === request.action.ref &&
    !Object.is(patchedDetails.result, request.value)   // identity, not deep-equality
) {
  return patchedDetails.result;
}
if (patchedContent !== content) return valueFromContent(patchedContent);
return request.value;
```

**Flow:** skip providers whose native lifecycle already fires middleware → serialize value to text content + wrap original in proxy-details envelope → emit synthetic `tool_result` through the host runner (abortable) → interpret patch by precedence: explicit `isError` throws; a details envelope with SAME ref and a **referentially different** result replaces the value; changed content becomes the value (`{content}` object preserved when non-text parts exist); otherwise the original wins.
**Invariant:** the unpatched path must be byte-identical passthrough — middleware that doesn't touch content/details can never flatten a structured value. Ref must match before a details patch is trusted (foreign envelopes ignored). The proxy runs BEFORE any maxNestedResultChars truncation of the nested result.
**Probe:** `tests/tool-result-proxy.test.ts:43` ("emits a namespaced nested tool_result and applies a content patch"), `:67` ("uses a proxy-details result patch without flattening structured values"), `:84` ("preserves the original value when middleware does not patch it"), `:104` ("turns an isError patch into a provider invocation failure"), `:139` ("runs the proxy before maxNestedResultChars is enforced").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "FabricToolResultProxy emitToolResult proxy details readFabricToolResultProxyDetailsV1 runAbortable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the precedence chain (isError-throw > same-ref details swap via Object.is > changed-content > original) and the abortable emission wrapper; adapt the envelope kind/ref constants to your protocol; omit the pi ExtensionRunner types.
