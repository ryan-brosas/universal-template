<!-- capsule-v2 -->
# Caution and verify — is communication props-down/events-up and is eslint enforcing Vue rules?

**Source:** Vue Style Guide Priority D; tooling. **Question:** Are risky Vue escape hatches avoided and Priority A/B rules verified in CI?

## Communication seam
**Path/Symbol:** parent/child Vue components.
**Signature:** emit events; no prop mutation; class-based scoped CSS.
**Data Shape:** `:value` + `@input` / `emit('update:todo', …)`.

### Decisive pattern
```vue
<script setup>
const props = defineProps({ todo: { type: Object, required: true } })
const emit = defineEmits(['delete', 'update:todo'])
</script>

<template>
  <button class="btn-close" @click="emit('delete')">×</button>
</template>

<style scoped>
.btn-close { /* not bare `button { }` */ }
</style>
```

**Flow:** **Priority D** — prefer **props down, events up** → no **`v-model` on prop fields** → no **`$parent`** mutation shortcuts → in **scoped CSS**, use **class selectors** not bare **element selectors** (performance + clarity) → emit **new objects** for prop updates (`emit('update:todo', { ...todo, text })`).
**Invariant:** child mutating prop object, `$parent` reach-in, or scoped `button {}` selector fails caution review.
**Probe:** grep `props\.\w+\s*=` in script; eslint-plugin-vue no-mutating-props.

## Verify seam
**Flow:** enable **eslint-plugin-vue** with **Priority A** as errors, **B** as warnings or errors per team → add **vuejs-accessibility** eslint where UI-heavy → run **`npm run lint`** + **`vitest`/`vue-tsc`** on changed SFCs → manual: keyed lists, multi-word registration, scoped styles on new components.
**Probe:**
```bash
eslint 'src/**/*.vue'
vue-tsc --noEmit
```

## Verdict
Props/events discipline, safe scoped CSS, eslint-plugin-vue gate on changed Vue files. Learning note: `vue-style-learning-note.md`.
