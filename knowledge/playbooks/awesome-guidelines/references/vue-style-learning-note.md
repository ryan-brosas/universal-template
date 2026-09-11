# Vue.js style guide — learning note

**Status:** deep ingest (2026-08-29). **Feeds:** `vue-style-*.md` capsules, `vue-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Vue Style Guide](https://vuejs.org/style-guide/) (primary) | Priority A–D rules from vuejs/docs |
| vuejs/docs `src/style-guide/*.md` (primary mirror) | Essential, strongly recommended, recommended, use-with-caution |
| `javascript-coding-practices` (secondary) | General JS — Vue guide defers on semicolons/quotes |
| `wcag-accessibility-practices` (secondary) | a11y for Vue UI — style guide mentions semantic HTML lightly |
| `frontend-markup-practices` (secondary) | HTML/CSS baseline for non-SFC markup |

**Scope:** **Vue 3** SFCs, Options API and Composition API. **Priority A** = error prevention (enforce in CI). **B** = strongly recommended. **C** = consistency defaults. **D** = avoid risky patterns.

## Mental model — rule tiers

1. **Essential (A)** — multi-word components, typed props, `:key` on v-for, no v-if+v-for, scoped styles.
2. **Components (B)** — one component per file, naming/casing conventions, props down/events up patterns in templates.
3. **Templates & order (B/C)** — simple expressions, computed split, attribute/directive order, shorthands consistency.
4. **Caution (D)** — no element selectors in scoped CSS; no prop mutation / `$parent` shortcuts.

## Decision tables

### Priority A — Essential

| Rule | Requirement |
|---|---|
| Multi-word names | Always multi-word except root `App` |
| Prop definitions | Typed/required/validator in committed code |
| v-for key | Always `:key` (required on components) |
| v-if + v-for | Never same element — computed filter or wrapper `<template>` |
| Scoped styling | All non-layout components scoped (scoped/CSS modules/BEM) |

### Priority B — Strongly recommended (naming/files)

| Topic | Rule |
|---|---|
| Files | One component per file when bundler available |
| SFC filename | PascalCase or kebab-case consistently |
| Base components | Prefix `Base`/`App`/`V` for presentational primitives |
| Coupled children | Parent name prefix (`TodoListItem` not `TodoItem`) |
| Word order | General → specific (`SearchInputQuery`) |
| Self-closing | Empty components self-close in SFC/string/JSX; not in-DOM |
| Template casing | PascalCase in SFC; kebab-case in in-DOM templates |
| JS/JSX casing | PascalCase imports and `name`; kebab in global-only apps OK |
| Full words | Avoid abbreviations in component names |
| Prop casing | camelCase in script; kebab-case in in-DOM templates |
| Multi-attr | One attribute per line when multiple attrs |
| Simple templates | Complex logic → computed/methods |
| Simple computed | Split complex computed into named steps |
| Quoted attrs | Always quote non-empty HTML attribute values |
| Directive shorthand | Always use `:`/`@`/`#` or never — pick one |

### Priority C — Recommended

| Topic | Rule |
|---|---|
| Options order | name → compiler → components → composition → props/emits → setup → data/computed → watch/lifecycle → methods → template |
| Attribute order | is → v-for → v-if/show → id → ref/key → v-model → attrs → v-on → v-html/text |

### Priority D — Use with caution

| Topic | Rule |
|---|---|
| Scoped CSS | Prefer class selectors over element selectors in scoped |
| Parent-child | Props down, events up — no v-model on prop, no `$parent` mutation |

## Anti-patterns

- Single-word component `<Item>` (non-App)
- `defineProps(['status'])` in production
- v-for without `:key`
- `v-for` + `v-if` on same node
- Global unscoped styles on feature components
- Multiple components in one file
- Mixed PascalCase and kebab-case filenames
- `MyButton` instead of `BaseButton`
- `TodoItem` when only used under `TodoList`
- `v-model` directly on prop object field
- Mutating props or reaching `$parent` state
- Element selectors in `<style scoped>`
- Complex expressions inline in `{{ }}`
- Mixed `v-bind:` and `:` in same codebase

## Skill trace

| Artifact | Role |
|---|---|
| `vue-style-essential-errors.md` | Priority A |
| `vue-style-components-naming.md` | Priority B naming/files |
| `vue-style-templates-composition.md` | Priority B/C templates |
| `vue-style-caution-verify.md` | Priority D + eslint verify |
| `vue-coding-practices/SKILL.md` | Vue review workflow |

## Relation to sibling skills

| Vue style | javascript-coding-practices |
|---|---|
| Component/prop/v-for rules | module/export/=== rules |
| SFC structure | N/A |
| eslint-plugin-vue | eslint general |

Architecture: Vue foundation / Pinia docs when building apps.
