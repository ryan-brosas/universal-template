# Angular coding style — learning note

**Status:** deep ingest (2026-08-29). **Feeds:** `angular-style-*.md` capsules, `angular-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Angular Style Guide (2025)](https://angular.dev/style-guide) (primary) | Naming, project structure, inject, components/directives, templates, lifecycle |
| angular/angular `adev/.../style-guide.md` (primary mirror) | Full 2025 revision (replaces suffix-based old guide) |
| [Component selectors](https://angular.dev/guide/components/selectors) (secondary) | Custom element hyphen, app prefix, no `ng` prefix |
| [Inputs/Outputs guides](https://angular.dev/guide/components/inputs) (secondary) | No DOM collision; camelCase outputs; no `on` prefix |
| `typescript-coding-standards` (secondary) | TS style deferred to Google TS guide per Angular doc |
| `vue-coding-practices` (secondary) | Parallel SPA conventions — Angular uses inject + feature folders |

**Scope:** **Angular application code** (components, directives, services, project layout). **Not:** Angular framework internals contribution style. **Legacy AngularJS** guide is out of scope.

**Consistency rule:** When this guide conflicts with an existing file, **prefer file consistency** unless intentionally modernizing.

## Mental model

2025 Angular style is **feature-first layout + signal-era components**:

1. **Naming/files** — kebab-case filenames matching class; `.spec.ts` colocated; shared base name for ts/html/css.
2. **Project structure** — `src/` + `main.ts`; feature directories not `components/`/`services/`; one concept per file.
3. **DI & class layout** — `inject()` over constructor; Angular APIs before methods; presentation-focused components.
4. **Templates & lifecycle** — simple templates/computed; `protected`/`readonly`; `[class]`/`[style]`; semantic handler names; thin lifecycle hooks + interfaces.

## Decision tables

### Naming

| Topic | Rule |
|---|---|
| File words | hyphen-separated (`user-profile.ts`) |
| Tests | same name + `.spec.ts` |
| Class match | filename reflects primary class (`UserProfile` → `user-profile.ts`) |
| Avoid | `helpers.ts`, `utils.ts`, `common.ts` junk drawers |
| Component trio | `user-profile.ts`, `.html`, `.css` same stem |
| Extra styles | `user-profile-settings.css` etc. |

### Project structure

| Topic | Rule |
|---|---|
| UI code | all under `src/` |
| Bootstrap | `src/main.ts` |
| Colocation | component ts/template/styles + spec same directory |
| Organization | **by feature** (`show-times/film-details/`) not by type |
| Split | when directory too large |
| One concept | one component/directive/service per file (small related group OK) |

### Dependency injection

| Topic | Rule |
|---|---|
| Prefer | `inject()` over constructor parameter injection |

### Components & directives

| Topic | Rule |
|---|---|
| Selectors | custom element with **hyphen** + **app prefix** (never `ng`) |
| Attribute directives | camelCase attr e.g. `[mrTooltip]` |
| Member order | injected deps, inputs, outputs, queries **before** methods |
| Focus | presentation in component; logic in services/functions |
| Templates | complex logic → computed/TS; not template soup |
| Template-only members | `protected` |
| Angular-init props | `readonly` on input/model/output/query signals |
| Styling bindings | `[class]`/`[style]` over `ngClass`/`ngStyle` |
| Event handlers | name for **action** (`saveUserData`) not `handleClick` |
| Lifecycle | thin hooks calling named methods; implement `OnInit` etc. |

### Inputs/outputs (linked guides)

| Topic | Rule |
|---|---|
| Names | avoid DOM property collisions |
| Prefix | no selector-style prefix on inputs/outputs |
| Outputs | camelCase; **no `on` prefix** |

## Anti-patterns

- `UserProfile.ts` PascalCase filename
- Tests in separate top-level `tests/` tree away from source
- `src/components/` + `src/services/` type-based folders
- Constructor injection when `inject()` is standard in codebase
- Public members only used in template
- Mutable `input()` signal property reassignment
- `ngClass`/`ngStyle` for simple class/style toggles
- `(click)="handleClick()"` on Save button
- Long logic inlined in `ngOnInit`
- Lifecycle hook without interface (`implements OnInit`)
- Component selector without hyphen or using `ng-` prefix
- Output named `onSave` or colliding with DOM event name
- Generic `utils.ts` accumulating unrelated code

## Skill trace

| Artifact | Role |
|---|---|
| `angular-style-naming-files.md` | filenames, spec colocation, component triplets |
| `angular-style-project-structure.md` | src, features, one concept per file |
| `angular-style-components-templates.md` | inject, members, templates, lifecycle |
| `angular-style-selectors-verify.md` | selectors, I/O names, eslint verify |
| `angular-coding-practices/SKILL.md` | Angular app review workflow |

## Relation to sibling skills

| Angular style | typescript-coding-standards |
|---|---|
| Angular-specific layout/APIs | Google TS general |
| inject(), signals inputs | TS types generally |
| Feature folders | N/A |

Compare SPA naming: `vue-coding-practices`.
