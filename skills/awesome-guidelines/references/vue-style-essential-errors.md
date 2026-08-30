<!-- capsule-v2 -->
# Essential errors — do components, props, lists, and styles prevent Vue footguns?

**Source:** Vue Style Guide Priority A. **Question:** Are Priority A rules satisfied so lists, props, and styles cannot silently break?

## Component seam
**Path/Symbol:** Vue SFC components and templates.
**Signature:** multi-word names; typed props; keyed v-for; scoped styles.
**Data Shape:** `<TodoItem />`; `defineProps({ status: { type: String, required: true } })`.

### Decisive pattern
```vue
<script setup>
const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (v) => ['syncing', 'synced', 'error'].includes(v),
  },
})
</script>

<template>
  <ul>
    <TodoItem v-for="todo in todos" :key="todo.id" :todo="todo" />
  </ul>
</template>

<style scoped>
.todo-item { /* class, not bare element */ }
</style>
```

**Flow:** **multi-word** component names always (except root **`App`**) → **detailed prop definitions** in committed code (type, required, validator) — array-only props for prototypes → **`v-for` always has `:key`** (mandatory on components) → **never `v-if` on same element as `v-for`** — filter with **computed** or wrap with **`<template v-for>`** + inner `v-if` → **component-scoped styling** (scoped, CSS modules, or BEM) on all non-layout components; libraries prefer class-based over scoped attr.
**Invariant:** `<Item>`, keyless v-for, v-if+v-for combo, or global feature styles fail Priority A review.
**Probe:** eslint-plugin-vue essential rules; grep `v-for` without `:key`.

## Verdict
Multi-word components, validated props, keyed lists, separated v-if/v-for, scoped styles. Learning note: `vue-style-learning-note.md`.
