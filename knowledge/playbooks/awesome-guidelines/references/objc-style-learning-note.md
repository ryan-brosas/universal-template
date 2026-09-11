# Objective-C style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `objc-style-*.md` capsules, `objc-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google Objective-C Style Guide](https://google.github.io/styleguide/objcguide.html) (primary) | 2-space indent; optional 80 cols; prefixes; Doxygen docs; property order; designated initializers; copy semantics; dot for properties only; umbrella imports; NSError over exceptions |
| [GitHub objective-c-style-guide](https://github.com/github/objective-c-style-guide) (secondary, archived) | Tomdoc/Tomdoc-style docs; `#pragma mark` layout; property copy/strong rules; ivar `_` prefix; dot for idempotent accessors; literals; early return; blocks spacing; category naming |

**Baseline:** Apple [Coding Guidelines for Cocoa](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/CodingGuidelines/CodingGuidelines.html) applies unless contradicted. Use project `clang-format` when present; Google spacing wins for new cross-team code.

## Mental model

Objective-C quality is **prefix-safe APIs + explicit ownership + readable headers**:

1. **Layout** — 2 spaces; braces on same line; colon-aligned multiline selectors; grouped imports.
2. **Naming/prefixes** — 3+ char class prefix; PascalCase types; camelCase methods; category method prefixes.
3. **Properties/memory** — copy immutable params; designated initializers; ivars in `.m`; no `+new`; init/dealloc avoid `self` messaging.
4. **Docs/errors** — Doxygen on public API; `#pragma mark` sections; `NSError **` not exceptions for flow; literals over verbose constructors.

## Decision tables

### Layout

| Topic | Rule |
|---|---|
| Indent | 2 spaces (Google); project may use tabs via clang-format (GitHub legacy) |
| Line length | 80 cols when project adopts Google C++ alignment |
| Braces | same line as `if`/`for`; both branches braced when `else` present |
| Methods | all args one line OR one arg per line with aligned colons |
| Imports | related header → system → C lib → project; blank line between groups |
| Frameworks | umbrella `@import UIKit` / `#import <Foundation/Foundation.h>` |
| Vertical space | sparing; no blank line just inside function braces |

### Naming & prefixes

| Entity | Convention |
|---|---|
| Classes/protocols | PascalCase; 3+ char prefix when shared (`GTMExample`) |
| Categories | `Class+PrefixFeature.h`; methods `prefix_feature` when shared |
| Methods | camelCase sentence-like; no `get` prefix on accessors |
| BOOL accessors | `-isGlorious` property `glorious`; dot only on property name |
| C functions | PascalCase; prefixed when non-static |
| Iv vars | leading `_` (`_bar`) |
| Globals | `g` prefix, rare |
| Acronyms | all caps inside name (`URL`, `ID`) |
| Constants | mixed case + prefix; `NS_ENUM` values extend typedef name |

### Properties & memory

| Case | Rule |
|---|---|
| Property order | properties → class methods → initializers → instance methods |
| Semantics | declare `nonatomic`/`copy`/`strong`/`weak` explicitly |
| Immutable exposure | `copy` on NSString/NSArray/etc.; `strong` only when mutable surface intended |
| Iv ars | in `@implementation`; only when type differs from property |
| Init | assign ivars directly; no redundant nil/0 init; `NS_DESIGNATED_INITIALIZER` |
| dealloc/init | avoid messaging `self`; direct ivar release/removeObserver |
| Dot syntax | properties only, not arbitrary methods |
| Literals | `@[]`, `@{}`, `@1`, boxed expressions |
| Copy | retain copy of mutable args in setters/init/async |

### Docs & errors

| Case | Rule |
|---|---|
| Headers | Doxygen on interfaces, properties, public methods |
| Nil params | document whether `nil` allowed |
| Marks | `#pragma mark` group lifecycle/drawing/protocols |
| Errors | `NSError **` out-parameters; exceptions for programmer error only |
| Tests | comment optional when name is self-explanatory |

## Anti-patterns

- Two-letter Apple-reserved prefixes
- Unprefixed category methods on shared classes
- `getDelegate`-style accessors
- `object.isGlorious` dot on BOOL getter method
- `frogs.reverseObjectEnumerator` dot on non-property method
- `@synthesize` without need
- `weak` long-lived references (GitHub smell)
- Accessing ivars outside init/dealloc/custom accessor
- `+new` or overriding `+new`
- Messaging `self` in `-init`/`-dealloc` for overridable methods
- Property access in designated initializer without direct ivar assign
- Individual Foundation subheaders instead of umbrella
- `#include` on ObjC headers
- Unsigned loop counters counting down
- Macros for constants/functions when const/inline suffices
- Exceptions for control flow
- Undocumented public selectors
- Mixed colon-alignment styles in one file

## Skill trace

| Artifact | Role |
|---|---|
| `objc-style-formatting-layout.md` | indent, braces, selectors, imports |
| `objc-style-naming-prefixes.md` | prefixes, categories, method names |
| `objc-style-properties-memory.md` | properties, init, copy, dot syntax |
| `objc-style-docs-errors.md` | Doxygen, marks, NSError, literals |
| `objc-coding-practices/SKILL.md` | clang-format + static analysis in CI |
