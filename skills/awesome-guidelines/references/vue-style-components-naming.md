<!-- capsule-v2 -->
# Component naming and files — are SFC files, prefixes, and casing consistent?

**Source:** Vue Style Guide Priority B (files, naming, casing). **Question:** Can developers find related components and register them without HTML/custom-element conflicts?

## File seam
**Path/Symbol:** `components/` tree, SFC filenames.
**Signature:** one component per file; PascalCase or kebab-case filenames.
**Data Shape:** `BaseButton.vue`; `TodoListItem.vue`.

### Decisive pattern
```
components/
  BaseButton.vue
  SearchInputQuery.vue
  SearchButtonRun.vue
  TodoList.vue
  TodoListItem.vue
```

**Flow:** **one component per file** when bundler available → filename **PascalCase** or **kebab-case** consistently (not mixed) → **base/presentational** components prefixed **`Base`/`App`/`V`** → **tightly coupled** child includes **parent prefix** (`TodoListItem` not `TodoItem`) → name order **general → specific** (`SearchButtonClear`) → **full words** not abbreviations → **empty** components **self-closing** in SFC/string/JSX; explicit close in in-DOM templates → **PascalCase** in SFC templates; **kebab-case** in in-DOM → **PascalCase** imports/`name` in JS/JSX → props declared **camelCase**; in-DOM templates use **kebab-case** attribute names → **multi-attribute** elements: one attr per line.
**Invariant:** mixed filename casing, unprefixed base button, or ambiguous `TodoItem` without parent context fails naming review.
**Probe:** list components/; eslint-plugin-vue component-name rules; import name vs file name check.

## Verdict
Discoverable file-per-component tree with Base prefix, parent-prefixed children, and consistent casing. Learning note: `vue-style-learning-note.md`.
