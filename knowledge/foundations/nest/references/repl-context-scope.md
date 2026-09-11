<!-- capsule-v2 -->
# ReplContext — how does the REPL expose the live container as an auto-completable global scope?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How are module members turned into REPL globals without collisions, and how do native commands register aliases and lazy help?

## initializeContext / introspectCollection / addNativeFunction / registerFunctionIntoGlobalScope
**Path/Symbol:** `packages/core/repl/repl-context.ts:initializeContext` (:53-75), `introspectCollection` (:77-112), `stringifyToken` (:114-120), `addNativeFunction` (:122-143), `registerFunctionIntoGlobalScope` (:145-163).
**Signature:** `constructor(app: INestApplicationContext, nativeFunctionsClassRefs?: ReplFunctionClass[])`; `globalScope = Object.create(null)`; `debugRegistry: Record<ModuleKey, {controllers, providers}>`.
**Data Shape:** Scope entries bind NAME → injection TOKEN (class refs or string tokens quoted via `stringifyToken`); InternalCoreModule is hidden; ApplicationConfig/self-named providers skipped; ModuleRef registered in scope but kept OUT of debugRegistry.

### Decisive source
```ts
let moduleName = moduleRef.metatype.name;
if (this.globalScope[moduleName]) moduleName += ` (${moduleRef.token})`;  // collision suffix

// token keying + first-wins:
if (!this.globalScope[stringifiedToken]) {
  Object.defineProperty(this.globalScope, stringifiedToken,
    { value: token, configurable: false, enumerable: true });   // enumerable = autocomplete
}

// aliases share the instance's prototype, not the function:
const aliasNativeFunction = Object.create(nativeFunction);
aliasNativeFunction.fnDefinition = { name: aliasName, description: ..., signature: ... };

Object.defineProperty(functionBoundRef, 'help', {
  enumerable: false, configurable: false,
  get: () => this.writeToStdout(nativeFunction.makeHelpMessage()),   // LAZY help
});
```

**Flow:** reach into `(app as any).container` (deliberate non-public accessor) → walk every module: rename-collide module names with token suffix → introspect providers+controllers into scope & registry → define module class on scope → instantiate each native function class ONCE, register under name + every alias (prototype-linked clones so state is shared), bind actions into scope with a non-enumerable lazy `help` getter.
**Invariant:** (1) `Object.create(null)` for globalScope — no Object.prototype pollution of completions (`hasOwnProperty` isn't a command). (2) First-seen token wins scope naming but ALL tokens still land in per-module debugRegistry — `get()`/`debug` can disambiguate what autocomplete collapsed. (3) Aliases must be prototype-clones (Object.create) rather than re-instantiations: two instances would split any state the action carries. (4) Help text renders lazily through a getter because it writes to stdout at CALL time, not registration.
**Probe:** `packages/core/test/repl/repl-context.spec.ts` (:4; writeToStdout :27) + `native-functions/` specs; `repl-native-commands.ts::defineDefaultCommandsOnRepl` documents the dual help contract (context getter vs commands property).
**Coverage caveat:** repl-context spec is thin (smoke-level) — deeper guarantees source-grounded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ReplContext globalScope nativeFunctions debugRegistry aliases", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any live-object inspector console (container-backed REPL, admin shell): null-proto scope, collision-suffixed names, prototype-shared aliases, lazy help getters; adapt the container accessor; omit debugRegistry if you lack a debug command. Porting wrong: plain `{}` scope (prototype keys pollute completion lists) or re-instantiating aliased commands (state divergence).
