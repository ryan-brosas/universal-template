<!-- capsule-v2 -->
# Preview mode + deterministic snapshots — how does the container support non-instantiating boot and reproducible identity?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What exactly does preview skip, and what must be seeded for deterministic UUIDs to hold?

## Injector preview + UuidFactory + InitializeOnPreviewAllowlist
**Path/Symbol:** `packages/core/injector/injector.ts:instantiateClass` (845-884, preview branch 859-862); `packages/core/nest-factory.ts:initialize` (UuidFactory.mode 220-222, createGraphInspector 387-394); `packages/core/injector/container.ts:setModule` (`shouldInitOnPreview` 170); `packages/core/inspector/uuid-factory.ts`.
**Signature:** `new Injector({ preview: boolean, snapshot?: boolean, instanceDecorator? })`.
**Data Shape:** `InitializeOnPreviewAllowlist` — a Set of module types allowed to instantiate under preview.

### Decisive source
```ts
// instantiateClass — preview marks resolved WITHOUT calling any constructor
if (this.options?.preview && !wrapper.host?.initOnPreview) {
  instanceHost.isResolved = true;
  return instanceHost.instance;
}
// nest-factory — snapshot flips ALL uuids to deterministic derivation
UuidFactory.mode = options.snapshot ? UuidFactoryMode.Deterministic : UuidFactoryMode.Random;
...
return appOptions?.snapshot ? new GraphInspector(container) : NoopGraphInspector;
```

**Flow:** create(..., {preview, snapshot}) → Injector/InstanceLoader built with the same options → scanner records full metadata graph → instantiation pass short-circuits per wrapper unless its MODULE is on the allowlist (InternalCoreModule self-registers) → hook runner filters modules by `initOnPreview`.
**Invariant:** Preview still runs the ENTIRE scan and prototype passes — only constructor invocation is skipped; `get()` on preview instances throws via `assertNotInPreviewMode` for lifecycle methods. Deterministic snapshots additionally require the opaque-key factory's 'shallow' strategy (container ctor reads `contextOptions.snapshot`) so module tokens are content-derived, not random.
**Probe:** `packages/core/test/nest-application-context.spec.ts::snapshot bootstrap` (:559) + inspector specs under `packages/core/test/inspector/`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "preview initOnPreview snapshot UuidFactory GraphInspector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt preview as a scan-only boot with an explicit allowlist for internal infrastructure; adapt allowlist contents to your framework internals; omit GraphInspector serialization if you don't need graph dumps. Porting wrong: treating preview instances as usable (isResolved true ≠ constructed) produces undefined-injection bugs instead of clean no-ops.
