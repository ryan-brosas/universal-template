---
title: angular-coding-practices
summary: Use when authoring or reviewing Angular apps, kebab-case files, feature folders, inject(), readonly inputs, protected template members, class/style bindings, selector prefixes, and angular-eslint verification.
kind: playbook
---

# Angular Coding Practices

Application skill for angular.dev Style Guide (2025). TypeScript style: `typescript-coding-practices`; domain modeling: `typescript-coding-standards`. SPA compare: `vue-coding-practices`.

## Core Principle

Use the installed Angular version and project conventions. The 2025 guide offers
feature-first layout, colocated files, injection, and signal patterns; it does not
require an unrelated app to migrate its layout or working constructor injection.
Treat the review prompts below as contextual checks, not automatic defects.

## When to Use / NOT

- Angular 17+ application components, directives, project layout.
- Migrating from legacy suffix-heavy style guide to 2025 conventions.
- PR review on `.ts`/`.html` in `src/`.

**NOT when:**

- Generic TypeScript style only, `typescript-coding-practices`.
- AngularJS 1.x, archived style guide.
- Framework package contributions, Angular repo CONTRIBUTING.

## Workflow

1. **Naming/files**, kebab-case, specs, triplets.
2. **Structure**, src, features, one concept.
3. **Components**, inject, templates, lifecycle.
4. **Selectors/verify**, selectors, I/O, lint.

## Red Flags

- PascalCase or camelCase source filenames
- Tests isolated in global `tests/` away from feature
- Type-based folders (`components/`, `services/`)
- Bootstrap entry not `src/main.ts`
- Constructor injection in new signal-era code without reason
- Public members only used in template
- Reassigning readonly input/model properties
- ngClass/ngStyle for simple static class/style toggles
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


## Related skills

- `typescript-coding-practices`, project TS style and optional Google baseline
- `typescript-coding-standards`, domain-modeling choices
- `wcag-accessibility-practices`, accessible templates
- `javascript-project-practices`, wider JS repo workflow
