---
name: angular-coding-practices
description: "Use when authoring or reviewing Angular apps, kebab-case files, feature folders, inject(), readonly inputs, protected template members, class/style bindings, selector prefixes, and angular-eslint verification."
disable-model-invocation: true
---

# Angular Coding Practices

Application skill for angular.dev Style Guide (2025) ingest (`awesome-guidelines`). TypeScript general: `typescript-coding-standards`. SPA compare: `vue-coding-practices`.

## Core Principle

Angular apps stay navigable with **feature-first `src/` layout**, **kebab-case colocated files**, **`inject()` + signal inputs**, **presentation-focused components**, and **hyphenated prefixed selectors** verified by angular-eslint.

## When to Use / NOT

- Angular 17+ application components, directives, project layout.
- Migrating from legacy suffix-heavy style guide to 2025 conventions.
- PR review on `.ts`/`.html` in `src/`.

**NOT when:**

- Generic TypeScript only, `typescript-coding-standards`.
- AngularJS 1.x, archived style guide.
- Framework package contributions, Angular repo CONTRIBUTING.

## Workflow

1. **Naming/files**, kebab-case, specs, triplets (`angular-style-naming-files.md`).
2. **Structure**, src, features, one concept (`angular-style-project-structure.md`).
3. **Components**, inject, templates, lifecycle (`angular-style-components-templates.md`).
4. **Selectors/verify**, selectors, I/O, lint (`angular-style-selectors-verify.md`).

## Red Flags

- PascalCase or camelCase source filenames
- Tests isolated in global `tests/` away from feature
- Type-based folders (`components/`, `services/`)
- Bootstrap entry not `src/main.ts`
- Constructor injection in new signal-era code without reason
- Public members only used in template
- Reassigning readonly input/model properties
- ngClass/ngStyle for simple static class/style toggles
- `(click)="handleClick()"` on labeled action buttons
- Long inlined ngOnInit logic
- Missing lifecycle interface (OnInit, etc.)
- Selector without hyphen or using `ng-` prefix
- Output prefixed with `on` or colliding with DOM event
- Generic utils/helpers files accumulating unrelated code
- Ignoring file-local consistency when bulk-reformatting

## Verification

- `ng lint` / @angular-eslint on changed paths
- `ng test` for colocated `.spec.ts`
- `ng build` or `tsc` strict template check
- Selector hyphen + app prefix audit on new components
- Capsule probes in review notes


## References

- `awesome-guidelines/references/angular-style-learning-note.md`
- `awesome-guidelines/references/angular-style-naming-files.md`
- `awesome-guidelines/references/angular-style-project-structure.md`
- `awesome-guidelines/references/angular-style-components-templates.md`
- `awesome-guidelines/references/angular-style-selectors-verify.md`

## Related skills

- `typescript-coding-standards`, Google TS baseline
- `wcag-accessibility-practices`, accessible templates
- `javascript-project-practices`, wider JS repo workflow
