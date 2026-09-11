<!-- capsule-v2 -->
# Prototype pre-pass — why does instantiation run twice (prototypes, then instances), and what does the first pass actually create?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What breaks if a porter deletes the prototype pass and instantiates in one go?

## InstanceLoader
**Path/Symbol:** `packages/core/injector/instance-loader.ts:InstanceLoader` (createInstancesOfDependencies 26-41, createPrototypes 43-50, createInstances 52-67).
**Signature:** `createInstancesOfDependencies(modules: Map<string, Module> = this.container.getModules()): Promise<void>`.
**Data Shape:** operates on all three collections per module (providers → injectables → controllers), both passes.

### Decisive source
```ts
public async createInstancesOfDependencies(modules = this.container.getModules()) {
  this.createPrototypes(modules);          // pass 1: bare prototype shells
  try {
    await this.createInstances(modules);   // pass 2: real constructors
  } catch (err) {
    this.graphInspector.inspectModules(modules);
    this.graphInspector.registerPartial(err);  // capture partial-init state for debugging
    throw err;
  }
  this.graphInspector.inspectModules(modules);
}
// pass 1 — never constructs; just Object.create(metatype.prototype) via loadPrototype
providers.forEach(wrapper => this.injector.loadPrototype<Injectable>(wrapper, providers));
```

**Flow:** for every module: prototypes of providers/injectables/controllers → then instances of the same, module-concurrently (`Promise.all` over modules, sequential within a module).
**Invariant:** Every wrapper has a non-null instance reference BEFORE any constructor runs — this is what makes forwardRef circular imports resolvable (partners can already hold each other's shells). The InternalCoreModule is excluded from "module initialized" log noise only.
**Probe:** `packages/core/test/injector/instance-loader.spec.ts` (prototype-then-instance ordering).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "InstanceLoader createPrototypes createInstancesOfDependencies", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-pass instantiate (shell prototypes for ALL wrappers first, then constructors); adapt graph-inspector hooks to your observability; omit logger whitelisting. Porting wrong: single-pass construction deadlocks or throws on circular graphs that the shell pre-pass makes trivially resolvable.
