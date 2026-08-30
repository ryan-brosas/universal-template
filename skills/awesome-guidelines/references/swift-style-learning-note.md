# Swift style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `swift-style-*.md` capsules, `swift-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Swift API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/) (primary) | clarity at point of use; doc comment per declaration; role-based naming; fluent call sites; argument labels; mutating/nonmutating pairs; defaulted parameters; protocol naming; acronym casing; avoid overload ambiguity |
| [GitHub Swift Style Guide](https://github.com/github/swift-style-guide) (secondary, archived) | `let` by default; `guard` early exit; avoid force-unwrap/IUOs; implicit getters; explicit top-level access control; colon with identifier; minimal `self`; prefer structs; `final` classes by default; omit redundant generic params on methods |

**Not duplicated here:** Full SwiftFormat rule matrix — project formatter config wins on indent (spaces vs tabs). SwiftUI/UIKit patterns — use stack capsules in `foundation-pack/`.

## Mental model

Swift style in this catalog is **API-design-first naming plus safe value-oriented defaults**:

1. **Safety & values** — `let` default, `guard` for early exit, optional binding over `!`, structs/`final` unless reference semantics required.
2. **Names at use site** — methods read as English phrases; omit redundant type words; name by role (`supplier`) not type (`WidgetFactory`).
3. **Labels & defaults** — argument labels encode grammar; defaulted params at end replace method families; factory methods start with `make`.
4. **Documentation** — every public declaration gets a `///` summary; non-O(1) properties document complexity.

## Decision tables

### Safety & access (GitHub + Swift norms)

| Topic | Rule |
|---|---|
| Binding | `let` unless mutation required |
| Early exit | `guard … else { return/throw/break }` |
| Optionals | `if let` / `?.` — avoid `!` and `Type!` |
| `self` | implicit except closures / name clashes |
| Top-level API | explicit `public`/`internal`/`private` |
| Types | prefer `struct`; classes `final` by default |
| Colon | `identifier: Type` with colon attached to name |

### Naming (API Design Guidelines)

| Element | Convention |
|---|---|
| Types/protocols | UpperCamelCase |
| Everything else | lowerCamelCase |
| Acronyms | uniform case per position (`utf8Bytes`, `isRepresentableAsASCII`) |
| Booleans | read as assertions (`isEmpty`, `intersects`) |
| Protocols (what it is) | noun (`Collection`) |
| Protocols (capability) | `…able` / `…ible` / `…ing` |
| Factory | `make…` prefix |

### Methods & labels

| Case | Rule |
|---|---|
| Side-effect free | noun phrase (`distance(to:)`) |
| Mutating | imperative verb (`sort()`, `append()`) |
| Nonmutating pair | `-ed`/`-ing` suffix (`sorted()`, `strippingNewlines()`) |
| Weak types | noun label before param (`addObserver(_:forKeyPath:)`) |
| Value-preserving conversion | no first arg label (`Int64(x)`) |
| Prepositional phrase | label from preposition (`remove(at:)`) |
| Defaults | prefer over method families; default args at end |

### Documentation

| Element | Rule |
|---|---|
| Coverage | `///` on every declaration |
| Summary | single sentence fragment; what it does/returns |
| Complexity | document non-O(1) computed properties |
| Methods vs functions | prefer methods/properties; free functions only when no `self` / domain notation |

## Anti-patterns

- `foo!` force-unwrap in production paths
- `var` when value never changes
- `removeElement(_:)` repeating type in name
- `func index()` and `func index(_:inTable:)` with different semantics (overload confusion)
- Overloading on return type only
- Method families instead of default parameters
- Missing doc summary on public API
- Non-`final` class without subclass plan
- Class inheritance where protocol + struct suffices

## Skill trace

| Artifact | Role |
|---|---|
| `swift-style-formatting-safety.md` | let, guard, optionals, access, struct/final |
| `swift-style-naming-api.md` | roles, fluency, acronyms, protocols |
| `swift-style-argument-labels.md` | labels, defaults, mutating pairs |
| `swift-style-documentation-types.md` | doc comments, methods vs functions |
| `swift-coding-practices/SKILL.md` | SwiftLint/SwiftFormat in CI |
