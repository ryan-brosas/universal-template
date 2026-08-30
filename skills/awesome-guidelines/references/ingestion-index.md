# Ingestion index — Kristories/awesome-guidelines

Source catalog: https://github.com/Kristories/awesome-guidelines

**Protocol:** `ingestion-protocol.md` — learn deep → learning note → capsule-v2 → application skill. **No shallow `ingested` rows.**

Status: `pending` | `deep` | `skip`

## Coverage summary (2026-08-29)

| Bucket | deep | skip | pending |
|---|---:|---:|---:|
| Cross-cutting (X-*) | 10 | 0 | 0 |
| Languages (L-*) | 40 | 1 | 0 |
| Platforms / frameworks / CMS | 21 | 0 | 0 |
| Tools / misc (T-*, O-*) | 0 | 5 | 0 |

**Catalog status:** Kristories/awesome-guidelines **ingestion complete** — all normative sections have a **deep** row (learning note + capsules + application skill) or a documented **skip**. With no pending rows, **continue** means router wiring, full `AGENTS.md` gate suite, or re-opening a documented skip — not another ingest slice unless the upstream catalog grows.

**Goal:** every Kristories/awesome-guidelines section represented here — learning note + capsules + application skill (or documented **skip** with reason).

## Cross-cutting (priority queue)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| X-01 | Git | `git-style-learning-note.md` | `git-style-branches.md`, `git-style-commit-messages.md`, `git-style-history-and-merge.md` | `git-workflow-and-versioning` | **deep** |
| X-02 | SemVer | `semver-learning-note.md` | `semver-public-api-and-bumps.md`, `semver-precedence-and-prerelease.md` | `git-workflow-and-versioning` | **deep** |
| X-03 | Keep a Changelog | `changelog-style-learning-note.md` | `changelog-human-curation.md` | `git-workflow-and-versioning`, `push-pr` | **deep** |
| X-04 | API | `api-design-learning-note.md` | `api-design-resource-names.md`, `api-design-http-idempotency.md`, `api-design-errors-machine-readable.md`, `api-design-pagination-and-lists.md`, `api-design-versioning-contract.md` | `api-design-practices` | **deep** |
| X-05 | Shell | `shell-style-learning-note.md` | `shell-style-scope-and-safety.md`, `shell-style-quoting-and-arrays.md`, `shell-style-control-flow-subshells.md`, `shell-style-structure-and-errors.md` | `shell-scripting-practices` | **deep** |
| X-06 | Frontend | `frontend-style-learning-note.md` | `frontend-html-semantics-accessibility.md`, `frontend-css-naming-selectors.md`, `frontend-css-structure-formatting.md`, `frontend-assets-delivery.md` | `frontend-markup-practices` | **deep** |

## Cross-cutting — phase 3

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| X-07 | SQL | `sql-style-learning-note.md` | `sql-style-naming-schema.md`, `sql-style-query-layout.md`, `sql-style-ddl-types.md`, `sql-style-query-patterns.md` | `sql-scripting-practices` | **deep** |
| X-08 | Markdown | `markdown-style-learning-note.md` | `markdown-style-document-layout.md`, `markdown-style-lists-code.md`, `markdown-style-links-media.md`, `markdown-style-tables-portability.md` | `markdown-writing-practices` | **deep** |

## Cross-cutting — phase 4

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| X-09 | JSON | `json-style-learning-note.md` | `json-style-syntax-properties.md`, `json-style-types-formats.md`, `json-style-envelope-errors.md`, `json-style-maps-paging.md` | `json-api-practices` | **deep** |

## Cross-cutting — phase 10

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| X-10 | PowerShell | `powershell-style-learning-note.md` | `powershell-style-formatting-layout.md`, `powershell-style-naming-commands.md`, `powershell-style-functions-tools.md`, `powershell-style-errors-security.md` | `powershell-scripting-practices` | **deep** |

## Languages (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-py | Python | `python-style-learning-note.md` | `python-style-layout-imports.md`, `python-style-naming-modules.md`, `python-style-exceptions-truthiness.md`, `python-style-defaults-types-main.md` | `python-coding-practices` | **deep** |
| L-ts | TypeScript | `typescript-style-learning-note.md` | `typescript-style-modules-imports.md`, `typescript-style-types-nullability.md`, `typescript-style-classes-api.md`, `typescript-style-verify.md` | `typescript-coding-practices` | **deep** |
| L-js | JavaScript | `javascript-style-learning-note.md` | `javascript-style-modules-exports.md`, `javascript-style-variables-equality.md`, `javascript-style-formatting-control.md`, `javascript-style-functions-disallowed.md` | `javascript-coding-practices` | **deep** |
| L-go | Go | `go-style-learning-note.md` | `go-style-formatting-naming.md`, `go-style-errors-flow.md`, `go-style-interfaces-apis.md`, `go-style-concurrency-context.md` | `go-coding-practices` | **deep** |
| L-rust | Rust | `rust-style-learning-note.md` | `rust-style-formatting-naming.md`, `rust-style-errors-result.md`, `rust-style-traits-interop.md`, `rust-style-api-predictability.md` | `rust-coding-practices` | **deep** |
| L-java | Java | `java-style-learning-note.md` | `java-style-formatting-imports.md`, `java-style-naming-types.md`, `java-style-exceptions-practices.md`, `java-style-javadoc-public-api.md` | `java-coding-practices` | **deep** |
| L-php | PHP | `php-style-learning-note.md` | `php-style-formatting-layout.md`, `php-style-files-namespaces.md`, `php-style-types-comparisons.md`, `php-style-classes-design.md` | `php-coding-practices` | **deep** |
| L-ruby | Ruby | `ruby-style-learning-note.md` | `ruby-style-formatting-layout.md`, `ruby-style-naming-files.md`, `ruby-style-methods-blocks.md`, `ruby-style-classes-exceptions.md` | `ruby-coding-practices` | **deep** |

## Languages — phase 2 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-kotlin | Kotlin | `kotlin-style-learning-note.md` | `kotlin-style-formatting-layout.md`, `kotlin-style-naming-files.md`, `kotlin-style-organization-classes.md`, `kotlin-style-idioms-api.md` | `kotlin-coding-practices` | **deep** |
| L-swift | Swift | `swift-style-learning-note.md` | `swift-style-formatting-safety.md`, `swift-style-naming-api.md`, `swift-style-argument-labels.md`, `swift-style-documentation-types.md` | `swift-coding-practices` | **deep** |
| L-csharp | C# / .NET | `csharp-style-learning-note.md` | `csharp-style-formatting-layout.md`, `csharp-style-naming-types.md`, `csharp-style-modern-idioms.md`, `csharp-style-exceptions-api.md` | `csharp-coding-practices` | **deep** |
| L-scala | Scala | `scala-style-learning-note.md` | `scala-style-formatting-layout.md`, `scala-style-naming-packages.md`, `scala-style-types-immutability.md`, `scala-style-control-api.md` | `scala-coding-practices` | **deep** |

## Languages — phase 5 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-cpp | C++ | `cpp-style-learning-note.md` | `cpp-style-formatting-headers.md`, `cpp-style-naming-types.md`, `cpp-style-ownership-raii.md`, `cpp-style-classes-api.md` | `cpp-coding-practices` | **deep** |

## Languages — phase 6 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-c | C | `c-style-learning-note.md` | `c-style-formatting-control.md`, `c-style-naming-types.md`, `c-style-headers-modules.md`, `c-style-macros-safety.md` | `c-coding-practices` | **deep** |

## Languages — phase 7 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-clojure | Clojure | `clojure-style-learning-note.md` | `clojure-style-layout-namespaces.md`, `clojure-style-naming-types.md`, `clojure-style-functions-idioms.md`, `clojure-style-data-safety.md` | `clojure-coding-practices` | **deep** |

## Languages — phase 8 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-lisp | Common Lisp | `lisp-style-learning-note.md` | `lisp-style-formatting-files.md`, `lisp-style-naming-symbols.md`, `lisp-style-packages-systems.md`, `lisp-style-clos-control.md` | `common-lisp-coding-practices` | **deep** |

## Languages — phase 9 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-d | D | `d-style-learning-note.md` | `d-style-formatting-layout.md`, `d-style-naming-types.md`, `d-style-declarations-api.md`, `d-style-docs-testing.md` | `d-coding-practices` | **deep** |

## Languages — phase 10 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-dart | Dart | `dart-style-learning-note.md` | `dart-style-formatting-names.md`, `dart-style-documentation.md`, `dart-style-usage-idioms.md`, `dart-style-design-api.md` | `dart-coding-practices` | **deep** |

## Languages — phase 11 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-delphi | Delphi / Object Pascal | `delphi-style-learning-note.md` | `delphi-style-formatting-layout.md`, `delphi-style-naming-types.md`, `delphi-style-units-structure.md`, `delphi-style-resources-errors.md` | `delphi-coding-practices` | **deep** |

## Languages — phase 12 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-elixir | Elixir | `elixir-style-learning-note.md` | `elixir-style-formatting-modules.md`, `elixir-style-naming-functions.md`, `elixir-style-expressions-pipelines.md`, `elixir-style-docs-types-errors.md` | `elixir-coding-practices` | **deep** |

## Languages — phase 13 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-elm | Elm | `elm-style-learning-note.md` | `elm-style-formatting-layout.md`, `elm-style-naming-modules.md`, `elm-style-types-declarations.md`, `elm-style-pipelines-expressions.md` | `elm-coding-practices` | **deep** |

## Languages — phase 14 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-emacs | Emacs Lisp | `emacs-lisp-style-learning-note.md` | `emacs-lisp-style-formatting-layout.md`, `emacs-lisp-style-naming-prefixes.md`, `emacs-lisp-style-functions-macros.md`, `emacs-lisp-style-packages-docs.md` | `emacs-lisp-coding-practices` | **deep** |

## Languages — phase 15 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-erlang | Erlang | `erlang-style-learning-note.md` | `erlang-style-formatting-modules.md`, `erlang-style-naming-types.md`, `erlang-style-control-flow.md`, `erlang-style-otp-security.md` | `erlang-coding-practices` | **deep** |

## Languages — phase 16 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-fsharp | F# | `fsharp-style-learning-note.md` | `fsharp-style-naming-documentation.md`, `fsharp-style-modules-types.md`, `fsharp-style-functions-async.md`, `fsharp-style-dotnet-interop.md` | `fsharp-coding-practices` | **deep** |

## Languages — phase 17 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-fortran | Fortran | `fortran-style-learning-note.md` | `fortran-style-formatting-layout.md`, `fortran-style-naming-modules.md`, `fortran-style-arrays-types.md`, `fortran-style-modern-api.md` | `fortran-coding-practices` | **deep** |

## Languages — phase 18 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-groovy | Groovy | `groovy-style-learning-note.md` | `groovy-style-syntax-idioms.md`, `groovy-style-objects-properties.md`, `groovy-style-collections-gdk.md`, `groovy-style-typing-api.md` | `groovy-coding-practices` | **deep** |

## Languages — phase 19 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-haskell | Haskell | `haskell-style-learning-note.md` | `haskell-style-formatting-layout.md`, `haskell-style-naming-imports.md`, `haskell-style-functions-control.md`, `haskell-style-types-io.md` | `haskell-coding-practices` | **deep** |

## Languages — phase 20 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-julia | Julia | `julia-style-learning-note.md` | `julia-style-formatting-layout.md`, `julia-style-modules-imports.md`, `julia-style-functions-methods.md`, `julia-style-docs-tests.md` | `julia-coding-practices` | **deep** |

## Languages — phase 21 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-lua | Lua | `lua-style-learning-note.md` | `lua-style-formatting-layout.md`, `lua-style-naming-modules.md`, `lua-style-functions-scope.md`, `lua-style-tables-docs.md` | `lua-coding-practices` | **deep** |

## Languages — phase 22 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-nim | Nim | `nim-style-learning-note.md` | `nim-style-formatting-layout.md`, `nim-style-naming-types.md`, `nim-style-procedures-api.md`, `nim-style-modules-verify.md` | `nim-coding-practices` | **deep** |

## Languages — phase 23 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-objc | Objective-C | `objc-style-learning-note.md` | `objc-style-formatting-layout.md`, `objc-style-naming-prefixes.md`, `objc-style-properties-memory.md`, `objc-style-docs-errors.md` | `objc-coding-practices` | **deep** |

## Languages — phase 24 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-pascal | Pascal | `pascal-style-learning-note.md` | `pascal-style-formatting-layout.md`, `pascal-style-naming-types.md`, `pascal-style-units-structure.md`, `pascal-style-comments-control.md` | `pascal-coding-practices` | **deep** |

## Languages — phase 25 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-perl | Perl | `perl-style-learning-note.md` | `perl-style-formatting-layout.md`, `perl-style-strict-scoping.md`, `perl-style-subs-io.md`, `perl-style-anti-patterns.md` | `perl-coding-practices` | **deep** |

## Languages — phase 26 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-r | R | `r-style-learning-note.md` | `r-style-formatting-syntax.md`, `r-style-naming-files.md`, `r-style-functions-pipes.md`, `r-style-docs-verify.md` | `r-coding-practices` | **deep** |

## Languages — phase 27 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-racket | Racket | `racket-style-learning-note.md` | `racket-style-formatting-textual.md`, `racket-style-naming-constructs.md`, `racket-style-modules-contracts.md`, `racket-style-testing-verify.md` | `racket-coding-practices` | **deep** |

## Languages — phase 28 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-solidity | Solidity | `solidity-style-learning-note.md` | `solidity-style-formatting-layout.md`, `solidity-style-naming-natspec.md`, `solidity-style-contract-structure.md`, `solidity-style-security-verify.md` | `solidity-coding-practices` | **deep** |

## Languages — phase 29 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-vb | Visual Basic | `vb-style-learning-note.md` | `vb-style-formatting-layout.md`, `vb-style-naming-types.md`, `vb-style-idioms-control.md`, `vb-style-docs-verify.md` | `vb-coding-practices` | **deep** |

## Languages — phase 30 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-xml | XML | `xml-style-learning-note.md` | `xml-style-schema-namespaces.md`, `xml-style-naming-values.md`, `xml-style-elements-attributes.md`, `xml-style-instances-verify.md` | `xml-markup-practices` | **deep** |

## Languages — phase 31 (ingest when stack matches)

| ID | Language | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| L-dotnet | .NET cross-cutting | `dotnet-style-learning-note.md` | `dotnet-style-naming-framework.md`, `dotnet-style-api-design.md`, `dotnet-style-exceptions-events.md`, `dotnet-style-security-verify.md` | `dotnet-coding-practices` | **deep** |

## Platforms — phase 1 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-android | Android | `android-style-learning-note.md` | `android-style-resources-layout.md`, `android-style-code-conventions.md`, `android-style-components-tests.md`, `android-style-architecture-verify.md` | `android-coding-practices` | **deep** |

## Platforms — phase 2 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-apache | Apache C (httpd) | `httpd-style-learning-note.md` | `httpd-style-formatting-indent.md`, `httpd-style-functions-flow.md`, `httpd-style-expressions-casts.md`, `httpd-style-comments-verify.md` | `httpd-c-coding-practices` | **deep** |

## Platforms — phase 3 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-arduino | Arduino | `arduino-style-learning-note.md` | `arduino-style-library-api.md`, `arduino-style-library-structure.md`, `arduino-style-sketch-code.md`, `arduino-style-packaging-verify.md` | `arduino-coding-practices` | **deep** |

## Platforms — phase 4 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-gnu | GNU C | `gnu-style-learning-note.md` | `gnu-style-formatting-layout.md`, `gnu-style-naming-files.md`, `gnu-style-comments-conditionals.md`, `gnu-style-constructs-portability.md` | `gnu-c-coding-practices` | **deep** |

## Platforms — phase 5 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-linux | Linux kernel | `linux-kernel-style-learning-note.md` | `linux-kernel-style-indent-braces.md`, `linux-kernel-style-naming-types.md`, `linux-kernel-style-functions-goto.md`, `linux-kernel-style-macros-verify.md` | `linux-kernel-coding-practices` | **deep** |

## Platforms — phase 6 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-mailchimp | Content (Mailchimp) | `mailchimp-style-learning-note.md` | `mailchimp-style-voice-tone.md`, `mailchimp-style-grammar-structure.md`, `mailchimp-style-inclusive-people.md`, `mailchimp-style-web-accessibility-i18n.md` | `mailchimp-content-practices` | **deep** |

## Platforms — phase 7 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-mozilla | MDN code examples | `mdn-style-learning-note.md` | `mdn-style-examples-principles.md`, `mdn-style-javascript-examples.md`, `mdn-style-html-examples.md`, `mdn-style-css-examples.md` | `mdn-code-examples-practices` | **deep** |

## Platforms — phase 8 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-google-docs | Google developer docs | `google-devdocs-style-learning-note.md` | `google-devdocs-style-voice-person.md`, `google-devdocs-style-format-headings.md`, `google-devdocs-style-procedures-links.md`, `google-devdocs-style-accessibility-global.md` | `google-devdocs-practices` | **deep** |

## Platforms — phase 9 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-node | Node.js | `node-style-learning-note.md` | `node-style-formatting-layout.md`, `node-style-functions-modules.md`, `node-style-conditionals-naming.md`, `node-style-platform-verify.md` | `node-coding-practices` | **deep** |

## Platforms — phase 10 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-mongo | MongoDB | `mongo-style-learning-note.md` | `mongo-style-enums-booleans.md`, `mongo-style-dates-null-types.md`, `mongo-style-names-ids.md`, `mongo-style-modelling-verify.md` | `mongodb-data-practices` | **deep** |

## Platforms — phase 11 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-wcag | Accessibility (WCAG 2.1) | `wcag-accessibility-learning-note.md` | `wcag-perceivable-media-text.md`, `wcag-operable-keyboard-focus.md`, `wcag-understandable-forms-language.md`, `wcag-robust-verify.md` | `wcag-accessibility-practices` | **deep** |

## Platforms — phase 12 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-webappsec | Secure web coding | `webappsec-style-learning-note.md` | `webappsec-auth-session.md`, `webappsec-input-output.md`, `webappsec-cross-domain-transport.md`, `webappsec-uploads-errors-verify.md` | `webappsec-coding-practices` | **deep** |

## Platforms — phase 13 (ingest when stack matches)

| ID | Section | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| P-project-js | JS projects | `js-project-learning-note.md` | `js-project-git-docs.md`, `js-project-env-deps-test.md`, `js-project-structure-style.md`, `js-project-api-a11y-verify.md` | `javascript-project-practices` | **deep** |

## Frameworks — phase 1 (ingest when stack matches)

| ID | Framework | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| F-django | Django | `django-style-learning-note.md` | `django-style-python-imports.md`, `django-style-templates-views.md`, `django-style-models-settings.md`, `django-style-misc-verify.md` | `django-coding-practices` | **deep** |

## Frameworks — phase 2 (ingest when stack matches)

| ID | Framework | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| F-symfony | Symfony | `symfony-style-learning-note.md` | `symfony-style-structure-control.md`, `symfony-style-naming-services.md`, `symfony-style-phpdoc-exceptions.md`, `symfony-style-verify.md` | `symfony-coding-practices` | **deep** |

## Frameworks — phase 3 (ingest when stack matches)

| ID | Framework | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| F-vue | Vue | `vue-style-learning-note.md` | `vue-style-essential-errors.md`, `vue-style-components-naming.md`, `vue-style-templates-composition.md`, `vue-style-caution-verify.md` | `vue-coding-practices` | **deep** |

## Frameworks — phase 4 (ingest when stack matches)

| ID | Framework | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| F-angular | Angular | `angular-style-learning-note.md` | `angular-style-naming-files.md`, `angular-style-project-structure.md`, `angular-style-components-templates.md`, `angular-style-selectors-verify.md` | `angular-coding-practices` | **deep** |

## CMS — phase 1 (ingest when stack matches)

| ID | CMS | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| CMS-wp | WordPress | `wordpress-style-learning-note.md` | `wordpress-style-php-naming.md`, `wordpress-style-security-escape.md`, `wordpress-style-database-i18n.md`, `wordpress-style-assets-verify.md` | `wordpress-coding-practices` | **deep** |

## CMS — phase 2 (ingest when stack matches)

| ID | CMS | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| CMS-drupal | Drupal | `drupal-style-learning-note.md` | `drupal-style-php-naming.md`, `drupal-style-namespaces-types.md`, `drupal-style-documentation-i18n.md`, `drupal-style-assets-verify.md` | `drupal-coding-practices` | **deep** |

## CMS — phase 3 (ingest when stack matches)

| ID | CMS | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| CMS-magento | Magento / Adobe Commerce | `magento-style-learning-note.md` | `magento-style-php-types.md`, `magento-style-class-di.md`, `magento-style-security-exceptions.md`, `magento-style-layers-verify.md` | `magento-coding-practices` | **deep** |

## CMS — phase 4 (ingest when stack matches)

| ID | CMS | Learning note | Capsules | Application skill | Status |
|---|---|---|---|---|---|
| CMS-october | October CMS | `october-style-learning-note.md` | `october-style-php-psr.md`, `october-style-naming-patterns.md`, `october-style-class-exceptions.md`, `october-style-packages-verify.md` | `october-coding-practices` | **deep** |

## Catalog backlog — pending rows

**No pending ingest rows.** Remaining catalog entries are documented **skip** below.

### Languages — skip (not pending)

| ID | Language | Primary source | Status |
|---|---|---|---|
| L-brainfuck | Brainfuck | BF Style Guide | **skip** (esoteric; no application skill) |

### Platforms / frameworks / CMS

_(all **deep** — queues complete.)_

### Tools — skip

| ID | Section | Primary source | Status |
|---|---|---|---|
| T-tools | Linters & release tools (ESLint, RuboCop, PHPCS, …) | awesome-guidelines Tools | **skip** — tool docs, not normative style text; use project linter config |
| T-agents-md | Agents.md format | agents.md | **skip** — covered by global `AGENTS.md` |

### Other catalog misc — skip

| ID | Section | Primary source | Status |
|---|---|---|---|
| O-robot | Robot Framework | robotframework.org user guide | **skip** — test framework manual, not code-style practices |
| O-codeql | CodeQL Coding Standards | github/codeql-coding-standards | **skip** — query-rule corpus for CodeQL, not application coding practices |
| O-indent | Indent style | Wikipedia | **skip** — encyclopedia meta, no actionable style guide |
| O-javaee | Java EE specification | javaee-spec | **skip** — platform spec; Java style covered by `java-coding-practices` |

## Deep ingest checklist

1. Read all primary + secondary sources (listed in learning note).
2. Write `references/<topic>-learning-note.md` (mental model, tables, anti-patterns, skill trace).
3. Write capsule-v2 per seam (`Flow`, `Invariant`, `Probe`).
4. Wire application skill References; update topic-index.
5. Mark `deep` here; run `skill-validator.py` (P0=0).
