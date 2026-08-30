# Android platform style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `android-style-*.md` capsules, `android-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [ribot android-guidelines — project_and_code_guidelines](https://github.com/ribot/android-guidelines/blob/master/project_and_code_guidelines.md) (primary) | Gradle structure; UpperCamelCase components; resource prefixes; layout/menu naming; Java m/s fields; 100-col lines; Intent/Fragment factories; XML id prefixes; tests |
| [ribot android-guidelines — architecture](https://github.com/ribot/android-guidelines/blob/master/architecture_guidelines/android_architecture.md) (primary) | MVP layers: View / Presenter / DataManager+helpers; Rx subscriptions; EventBus only for broadcast |
| [xmartlabs Android-Style-Guide](https://github.com/xmartlabs/Android-Style-Guide) (secondary) | 120 cols; no extra vertical whitespace in class; `@Nullable`/`@NonNull`; fragment/activity naming; field groups; layout attr order; string-array via `@string` refs |
| [ribot README → Jetpack](https://developer.android.com/jetpack/) (secondary) | legacy doc unmaintained; prefer Jetpack for new architecture |

**Scope:** Android app modules (Java/Kotlin). **Kotlin syntax:** `kotlin-coding-practices` + [Android Kotlin style](https://developer.android.com/kotlin/style-guide). **.NET backend:** not here. ribot MVP/Rx is historical — map concepts to ViewModel/Repository/Jetpack when greenfield.

## Mental model

Android platform quality is **resource naming discipline + component factories + layered UI/data split**:

1. **Resources/layout** — lowercase_underscore assets; `activity_*`/`fragment_*` layouts; prefixed ids/strings.
2. **Code style** — component suffix classes; m/s fields (Java legacy) or Kotlin conventions; import order; line wrap rules.
3. **Components** — `getStartIntent` / `newInstance`; prefixed Intent/Bundle keys; lifecycle-ordered overrides.
4. **Architecture/verify** — View↔Presenter↔DataManager separation (or Jetpack equivalent); lint; debug logging gated.

## Decision tables

### Project & resources (ribot + xmartlabs)

| Entity | Convention |
|---|---|
| Gradle layout | standard Android Gradle structure |
| Component classes | UpperCamelCase + suffix (`SignInActivity`, `UserFragment`) |
| Drawables/layouts | lowercase_underscore; prefixes `ic_`, `btn_`, `activity_`, `fragment_`, `item_` |
| Menu files | `activity_user.xml` in `menu/` (no redundant `menu_` in name) |
| Values files | plural: `strings.xml`, `colors.xml` |
| View ids | `{context}_{name}_{viewType}` snake (xmartlabs) or `{element}_` prefix (ribot) |
| Styles | UpperCamelCase names |
| String arrays | items reference `@string/…`; separate file from strings |

### Java/Kotlin code

| Topic | Rule |
|---|---|
| Exceptions | never empty catch; no generic `catch (Exception)` |
| Imports | no wildcards; android → third-party → java/javax → project |
| Fields (Java ribot) | `m` private instance, `s` private static, constants ALL_CAPS |
| Indent | 4 spaces; 8 for wrap continuation (ribot) or Google 120 cols (xmartlabs) |
| Line length | 100 (ribot) / 120 (xmartlabs) — pick project standard |
| Acronyms | treat as words (`XmlHttpRequest`) |
| Annotations | `@Override` required; `@Nullable`/`@NonNull` (xmartlabs) |
| Logging | `TAG` constant; verbose/debug off in release |
| Member order | constants → fields → ctor → overrides (lifecycle order) → public → private |
| Parameters | `Context` first; callbacks last |
| Keys | `PREF_`, `BUNDLE_`, `ARGUMENT_`, `EXTRA_`, `ACTION_` prefixes |

### Components & tests

| Case | Rule |
|---|---|
| Activity entry | `getStartIntent(Context, …)` before `onCreate` |
| Fragment entry | `newInstance(…)` + private argument keys |
| Unit tests | `TargetClassTest`; `methodPreconditionExpected` |
| Espresso | `ActivityTest`; chain each matcher on new line |

### Architecture (ribot MVP → modern mapping)

| Layer | Responsibility |
|---|---|
| View | Activities/Fragments/Compose UI; forwards input |
| Presenter | subscribes to data; maps to view calls (→ ViewModel) |
| DataManager | composes helpers; Rx/operators (→ Repository/UseCase) |
| Helpers | API/DB/Preferences single-purpose (→ Retrofit/Room/DataStore) |
| Event bus | only cross-screen broadcast events |

## Anti-patterns

- Empty catch blocks
- `catch (Exception e)` umbrella handler
- Wildcard imports
- Finalizers for cleanup
- Public Intent/Fragment keys when factory methods exist
- Layout file not matching component (`sign_in.xml` vs `SignInActivity`)
- Drawable without type prefix (`star.png` vs `ic_star.png`)
- String literals inside `<string-array>` items
- Verbose/debug logs in release leaking PII
- Presenter doing Android framework work directly
- DataManager exposing UI-specific formatting
- EventBus for single-screen events
- Multiple blank lines inside class body (xmartlabs)
- Nested ternary harming readability
- Interface names prefixed with `I` (xmartlabs)
- `List` entity fragment named plural incorrectly (`CustomersListFragment` vs `CustomerListFragment`)

## Skill trace

| Artifact | Role |
|---|---|
| `android-style-resources-layout.md` | drawables, layouts, strings, XML order |
| `android-style-code-conventions.md` | Java/Kotlin fields, imports, wrap, logs |
| `android-style-components-tests.md` | factories, keys, lifecycle, tests |
| `android-style-architecture-verify.md` | MVP/Jetpack layers, lint, logging |
| `android-coding-practices/SKILL.md` | lint/detekt/Gradle verify in CI |

## Modern note

Greenfield apps: prefer **Jetpack** (ViewModel, Navigation, Room/DataStore, Compose) while keeping ribot/xmartlabs **naming and resource** rules. Map MVP roles rather than copying RxJava boilerplate verbatim.
