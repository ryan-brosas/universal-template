<!-- capsule-v2 -->
# Templates and composition — are expressions simple and attributes ordered consistently?

**Source:** Vue Style Guide Priority B/C (templates, computed, attribute order). **Question:** Do templates stay declarative with community-default ordering?

## Template seam
**Path/Symbol:** SFC `<template>` and script computed/methods.
**Signature:** simple `{{ }}`; split computed; quoted attrs; consistent directive shorthands.
**Data Shape:** `{{ normalizedFullName }}` backed by computed.

### Decisive pattern
```vue
<template>
  <SearchInput
    :id="inputId"
    v-model="query"
    :placeholder="placeholder"
    @input="onInput"
  />
</template>

<script setup>
const normalizedFullName = computed(() =>
  fullName.value.split(' ').map(capitalize).join(' ')
)
</script>
```

**Flow:** **simple expressions** in templates — move complex logic to **computed** or **methods** → split **complex computed** into named steps (`basePrice`, `discount`, `finalPrice`) → **quote** non-empty HTML attribute values → **directive shorthands** (`:`, `@`, `#`) used **always or never** project-wide → **attribute order**: `is` → `v-for` → `v-if`/`v-show` → `id` → `ref`/`key` → `v-model` → other attrs → `v-on` → `v-html`/`v-text` → **options order** in Options API: name → compiler → components/directives → extends/mixins → props/emits → setup → data/computed → watch/lifecycle → methods → template.
**Invariant:** multi-line expression soup in mustache or random attribute order without team convention fails template review.
**Probe:** eslint-plugin-vue attribute order + max template complexity review.

## Verdict
Declarative templates, decomposed computed, quoted attrs, consistent shorthands and ordering. Learning note: `vue-style-learning-note.md`.
