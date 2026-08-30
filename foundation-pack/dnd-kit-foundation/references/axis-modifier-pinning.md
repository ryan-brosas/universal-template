<!-- capsule-v2 -->
# Axis modifier — declarative transform pinning via the descriptor configurator

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does a one-option modifier constrain drags to a single axis and get pre-configured as an exported constant?

## AxisModifier
**Path/Symbol:** `packages/abstract/src/modifiers/axis.ts:28-77`.
**Signature:** `class AxisModifier extends Modifier<DragDropManager, {axis: 'x'|'y', value: number}>` with `apply({transform}) => {...transform, [axis]: value}`; `static configure = configurator(AxisModifier)`; exports `RestrictToVerticalAxis = AxisModifier.configure({axis:'x', value:0})` / `RestrictToHorizontalAxis` (y→0).
**Data Shape:** modifiers compose in ARRAY ORDER inside `dragOperation.transform` (each receives `{...snapshot, transform}` from the previous); no options ⇒ identity passthrough (`apply` guards `!this.options`).

### Decisive source
```ts
apply({transform}: DragOperation) {
  if (!this.options) {
    return transform;
  }
  const {axis, value} = this.options;
  return {
    ...transform,
    [axis]: value,
  };
}
```

**Flow:** operation.transform derived getter folds position.delta through each modifier instance in order → AxisModifier overwrites ONE axis with its fixed value → downstream modifiers see the pinned transform. Because instances are created fresh per drag source (manager-kernel effect), the same configured descriptor can serve many simultaneous managers without shared state.
**Invariant:** modifiers must be pure functions of their snapshot input — caching or mutating `operation.transform` breaks composition order semantics; the options guard makes bare-constructor registration legal (descriptor normalization supplies undefined options).
**Probe:** modifier application + lifecycle matrix pinned by `packages/abstract/tests/manager-modifiers.test.ts` (:28-79 apply/preference, :82-256 destroy accounting) — executed GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "AxisModifier", name_pattern: "^AxisModifier$", limit: 10 });
```

## Verdict
Adopt the pure fold-over-snapshot modifier contract; adapt option vocabulary to your constraint needs (snap/restrict twins live beside this file); omit the pre-configured constants if your API takes descriptors inline.
