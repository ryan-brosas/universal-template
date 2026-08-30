<!-- capsule-v2 -->
# LayerNode tag/hoist/compile — how do per-tenant service trees share process-global singletons?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how does one dependency graph serve N per-directory service instances while compiling global singletons exactly once?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/effect/layer-node.ts`: `Node` (:24-34), `tags` (:66-88), `make` (:91-107), `unbound` (:109-116), `group` (:118-120), `hoist` (:232-272), `compile` (:274-294), `replacementMapFrom` (:296-310); `packages/core/src/effect/app-node.ts` (tags config, 14L); `packages/core/src/location-services.ts`: `buildLocationServiceMap` (:83-113).
**Signature:** `hoist<A, E, T extends Tag>(root: Node<A,E,any>, tag: T, replacements?): {node: Node<A,E>; hoisted: Node<unknown,E>}`; `compile<A,E>(root, replacements?): Layer.Layer<A,E>`.
**Data Shape:** Node = `{kind: "layer"|"unbound"|"group", name (= service key or explicit), implementation?, dependencies, tag?}`; app-node tags config `{location: ["global"], global: []}` — a location node may depend on global-tagged nodes, never the reverse (compile-time CheckTags).

### Decisive source
```ts
// location-services.ts — the per-directory boot:
const location = LayerNode.hoist(locationServices, Node.tags.values.global, allReplacements)
return LayerNode.compile(location.node).pipe(
  Layer.fresh,
  ...
  Layer.provide(LayerNode.compile(location.hoisted)),
)
```
```ts
// layer-node.ts — replacements are name-keyed, tag-checked, and rewritten into each other:
if (source.name !== replacementNode.name) throw new Error(`Cannot replace ${source.name} with ${replacementNode.name}`)
if (source.tag !== replacementNode.tag) throw new Error(`Cannot replace ${source.name} across tags`)
```

**Flow:** every v2 service exports a Node (`makeGlobalNode`/`makeLocationNode` from app-node tags) listing its deps as Nodes — deps are type-checked against the implementation's required services (`CheckDependencies` emits a "Missing dependencies" marker type). `compile()` walks the tree (cycle-detecting with a visiting set + stack, cached, replacement-resolving by node name), flattens groups, and `Layer.provide`s dependency layers into each implementation, then `provideMerge`-reduces the flattened list. `unbound()` marks a service required-but-unimplemented; compile throws "Unbound layer node" if one survives; `hasUnbound()` probes the tree (AppNodeBuilder.build uses it to auto-create the LocationServiceMap global node when needed). `hoist(root, tag)` extracts every tag-carrying node into a separate group (conflicting implementations of the same name under one tag → throw), replacing them in the tree with empty groups — buildLocationServiceMap hoists global-tagged nodes out of the 36-service locationServices group, compiles the hoisted group ONCE, and compiles the remaining location tree `Layer.fresh` per Location.Ref inside a LayerMap with 60-min idle TTL. Replacements are rewritten into the dependencies of every other replacement (`rewriteReplacementDependencies`) because a replacement can introduce new tagged dependencies (Location.boundNode depends on Project) that only the hoist walk can slice back out.
**Invariant:** tag direction (location→global only) is enforced at the type level; replacement name+tag must match the source; cycles throw with the full path; the hoisted group compiles once regardless of tenant count.
**Probe:** `packages/core/test/location-layer.test.ts` (4 it.live: cached services across constructed/decoded refs, per-directory state isolation with shared policy, per-location model resolution failure, plugin install into a location) + `packages/core/test/permission.test.ts` / `skill-discovery.test.ts` (both boot real trees through AppNodeBuilder.build with node replacements).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "LayerNode hoist compile tags unbound replacement idleTimeToLive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tag/hoist/compile split for any multi-tenant service graph: tag global singletons, hoist them out of the tenant tree, compile once, provide into every tenant layer compiled fresh. Adopt name+tag-checked replacements with dependency rewriting. Adapt the LayerMap TTL and Effect Layer primitives to your host. Omit the Effect-specific type-level dependency checking if your host lacks it — but keep a runtime unbound-check. Coverage caveat: LayerNode itself has no dedicated unit test file; it is exercised through every AppNodeBuilder.build-based test (location-layer, permission, skill-discovery read this pass).
