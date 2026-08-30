<!-- capsule-v2 -->
# Registered tool capture — how do you observe every host-registered tool without removing any from the host registry?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does an extension snapshot every registered tool (including tools from other extensions) into its own catalog while keeping them visible to the host and to permission-gating extensions?

## Prototype-hub capture over getAllRegisteredTools
**Path/Symbol:** `src/capture/interceptor.ts:installRegisteredToolCapture` (:131-172), `captureHub` (:65-88), `extensionRunnerConstructors` (:112-129); `src/capture/catalog.ts:CapturedToolCatalog.replace` (:34-58).
**Signature:** `installRegisteredToolCapture(options: {anchorDefinition: ToolDefinition; catalog: CapturedToolCatalog; initialPolicy?: FabricToolCaptureConfig; onCatalogRefresh?: () => void}): Promise<RegisteredToolCaptureController>` where controller = `{setPolicy(config), dispose()}`.
**Data Shape:** hub = `{listeners: Set<(tools, runner) => tools>}` stored non-configurable/non-writable under `Symbol.for("pi-fabric.registered-tool-capture.v1")` on the Runner **prototype**; catalog entries = `{name, definition, registeredTool, sourceInfo, runner, wrappedTool, risk}` keyed by tool name.

### Decisive source
```ts
const HUB_SYMBOL = Symbol.for("pi-fabric.registered-tool-capture.v1");
// One hub per Runner prototype; every instance shares it.
prototype.getAllRegisteredTools = function getFabricVisibleTools(): RegisteredTool[] {
  let tools = original.call(this);
  for (const listener of [...hub.listeners]) tools = listener(tools, this);
  return tools;                      // OBSERVE-ONLY: listener returns the same list
};
// Anchor self-identification survives wrapper objects via prototype walk:
const anchor = tools.find(
  (tool) =>
    (tool.definition as unknown as Record<PropertyKey, unknown>)[ANCHOR_SYMBOL] ===
      anchorToken || definitionDelegatesTo(tool.definition, options.anchorDefinition),
);                                   // proto-chain walk
if (!anchor) return tools;           // never attach to a foreign same-named tool
options.catalog.replace(tools, runner, policy, anchor.sourceInfo.path);
options.onCatalogRefresh?.();        // ownership re-assertion hook AFTER each refresh
return tools;
```
```ts
// catalog.ts — remember the runner BEFORE the enabled gate:
this.#runner = runner;
this.#tools.clear();
if (!config.enabled) return;
...
risk: config.risks[definition.name] ?? config.defaultRisk,
```

**Flow:** install patches every reachable ExtensionRunner constructor prototype (imported class PLUS the host package's own copy resolved by walking up from `process.argv[1]` to a `package.json` named `@earendil-works/pi-coding-agent`, plus `$PI_PACKAGE_DIR`) → each `getAllRegisteredTools()` call runs listeners in insertion order → the fabric listener finds its anchored tool (own-source path excluded from capture), replaces the whole catalog, fires `onCatalogRefresh` → returns the list untouched.
**Invariant:** capture is observation, never filtering — tools stay registered so permission/auditor extensions calling `getAllTools()` still see them (hiding from the model happens only in the active set, see core-tool-ownership). The anchor token check prevents hijacking an unrelated extension's tool that merely shares the name. Catalog replacement is total (`clear()` then refill) so removed tools disappear; `setPolicy(disabled)` and `dispose()` clear the catalog; the remembered runner is deliberately kept even when disabled so nested pi.* lifecycle replay keeps working.
**Probe:** `tests/tool-capture.test.ts:47` ("captures every extension tool while keeping it in Pi's registry"), `:114` ("does not attach to an unrelated tool with the Fabric tool name"), `:136` (dynamic update + disable clears), `:174` (refresh notification fires).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "installRegisteredToolCapture captureHub CapturedToolCatalog replace wrapRegisteredTool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Symbol-keyed prototype hub + observe-only listener + anchor-token self-ID + refresh callback pattern for any "mirror the host tool registry" port; adapt the host-package discovery to your CLI layout; omit the pi-specific provider names. Caveat: multi-copy host module graphs need the constructor enumeration or you patch the wrong copy.
