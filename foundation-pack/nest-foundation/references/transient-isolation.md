<!-- capsule-v2 -->
# Transient scope isolation — how does each consumer of a transient provider get its own instance, including TRANSIENT→TRANSIENT chains?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the effective-inquirer rule that keeps nested transients from being shared across parents?

## getEffectiveInquirer / getStaticTransientResolutionContext
**Path/Symbol:** `packages/core/injector/injector.ts:getEffectiveInquirer` (1073-1086), `getEffectiveInquirerId` (1088-1111), `getStaticTransientResolutionContext` (1113-1132); `instance-wrapper.ts:attachRootInquirer` (470-480).
**Signature:** `getEffectiveInquirerId(dependency, resolutionContext, parentInquirer): string | undefined`.
**Data Shape:** effective inquirer id is a composed string `"baseInquirerId:inquirer.id"` for static nested transients.

### Decisive source
```ts
/**
 * For nested TRANSIENT dependencies (TRANSIENT -> TRANSIENT) in non-static contexts,
 * returns parentInquirer to ensure each parent TRANSIENT gets its own instance.
 * ... For non-TRANSIENT -> TRANSIENT, returns inquirer.
 */
if (dependency?.isTransient && inquirer?.isTransient && parentInquirer) {
  if (contextId === STATIC_CONTEXT) return inquirer.getRootInquirer() ?? parentInquirer;
  return parentInquirer;
}
return inquirer;

// static-context composition: chain the ids so every nesting level keys distinctly
const baseInquirerId = effectiveInquirerId ?? this.getInquirerId(parentInquirer);
return `${baseInquirerId}:${inquirer.id}`;
```
```ts
// resolveConstructorParams — inherit root when the CURRENT inquirer is transient too
if (resolutionContext.inquirer?.isTransient && parentInquirer) {
  resolutionContext.inquirer.attachRootInquirer(parentInquirer);  // root = nearest non-transient
}
```

**Flow:** resolving a dep → if both dependency and current inquirer are transient, re-key the context by parent (request ctx) or composed id chain (static ctx) → InstanceWrapper routes storage through the two-level transientMap keyed by that effective id.
**Invariant:** A DEFAULT→TRANSIENT edge resolves once (static, shared); a TRANSIENT→TRANSIENT edge must produce a fresh instance per parent; REQUEST-scoped parents each isolate their own transient subtree. The composed-id scheme is what makes `transientMap.get(effectiveId)` distinct per chain position.
**Probe:** `packages/core/test/injector/nested-transient-isolation.spec.ts` (instanceCount assertions across two request parents) + `packages/core/test/scope/transient-scope.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "getEffectiveInquirer transient attachRootInquirer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt effective-inquirer re-keying with composed id chains for nested transients; adapt naming/format of composite keys freely; omit durable-tree interactions if not porting request scope. Porting wrong: keying nested transients only by their immediate inquirer makes siblings share leaf instances.
