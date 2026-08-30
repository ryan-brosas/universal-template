---
name: vue-coding-practices
description: "Use when authoring or reviewing Vue 3 SFCs — Priority A multi-word components, typed props, keyed v-for, scoped styles, naming conventions, template simplicity, props-down/events-up, and eslint-plugin-vue."
disable-model-invocation: true
---

# Vue Coding Practices

Application skill for official Vue Style Guide ingest (`awesome-guidelines`). Generic JS: `javascript-coding-practices`. a11y: `wcag-accessibility-practices`. HTML/CSS: `frontend-markup-practices`.

## Core Principle

Vue maintainability is **tiered style guide discipline** — Priority A prevents errors, Priority B naming keeps components discoverable, templates stay declarative, and parent-child state flows props down / events up.

## When to Use / NOT

- Vue 3 SFCs, Options API or Composition API.
- Component library layout, eslint-plugin-vue setup, PR review on `.vue` files.

**NOT when:**

- React/Svelte — use stack capsules in `foundation-pack/`.
- Pure JS utilities outside Vue — `javascript-coding-practices`.
- Full app architecture (Pinia routing) — Vue/Pinia foundation docs.

## Workflow

1. **Essential (A)** — names, props, keys, styles (`vue-style-essential-errors.md`).
2. **Naming/files (B)** — component tree conventions (`vue-style-components-naming.md`).
3. **Templates (B/C)** — expressions, order, shorthands (`vue-style-templates-composition.md`).
4. **Caution/verify (D)** — props/events, eslint (`vue-style-caution-verify.md`).

## Red Flags

- Single-word component name (non-App)
- Untyped `defineProps(['x'])` in committed code
- v-for without `:key`
- v-if and v-for on same element
- Unscoped styles on feature components
- Multiple components in one registration file
- Mixed PascalCase and kebab-case SFC filenames
- Unprefixed presentational `Button.vue`
- Child name without parent prefix when tightly coupled
- Abbreviated component filenames (`UProfOpts.vue`)
- v-model bound directly to prop field
- Mutating props or using `$parent` for state
- Element selectors in `<style scoped>`
- Complex expression chains in `{{ }}`
- Mixed `v-bind:` and `:` shorthands
- Unquoted HTML attribute values

## Verification

- eslint-plugin-vue on changed `.vue` files (Priority A rules as errors)
- vue-tsc / volar typecheck if TypeScript
- Vitest component tests on changed behavior
- Manual v-for key and scoped style spot check
- Capsule probes cited in review notes

## Skill Result Contract

```xml
<skill_result>
  <skill>vue-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>vue diff, eslint output, test log</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>keyless list, prop mutation, or Priority A violation</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/vue-style-learning-note.md`
- `awesome-guidelines/references/vue-style-essential-errors.md`
- `awesome-guidelines/references/vue-style-components-naming.md`
- `awesome-guidelines/references/vue-style-templates-composition.md`
- `awesome-guidelines/references/vue-style-caution-verify.md`

## Related skills

- `javascript-coding-practices` — script block JS habits
- `wcag-accessibility-practices` — accessible Vue UI
- `typescript-coding-standards` — typed Vue + TS projects
