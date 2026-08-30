# .NET cross-cutting style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `dotnet-style-*.md` capsules, `dotnet-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Framework Design Guidelines digest](https://github.com/dotnet/runtime/blob/v7.0.11/docs/coding-guidelines/framework-design-guidelines-digest.md) (primary) | Scenario-driven API; Pascal/camel; suffixes; aggregate components; collections over arrays; exceptions not error codes; IDisposable; overload patterns |
| [.NET Naming Guidelines](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/naming-guidelines) + linked capitalization/general pages (primary) | Public/protected naming required; CLR type names; semantic names; API versioning names |
| [Secure coding guidelines for .NET](https://learn.microsoft.com/en-us/dotnet/standard/security/secure-coding-guidelines) (primary) | No CAS/APTCA/partial trust; no Remoting/DCOM/binary formatters; validate untrusted input; library resource demands |
| [Framework Design Guidelines (book overview)](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/) (secondary) | Canonical reusable-library guidance; always/never convention tiers |

**Scope:** Cross-language .NET **public API and security baseline** (libraries, shared components, multi-language repos). Language syntax/layout: load `csharp-coding-practices`, `vb-coding-practices`, or `fsharp-coding-practices`. Stack patterns (ASP.NET, etc.): load stack capsules in `foundation-pack/`.

## Mental model

.NET cross-cutting quality is **scenario-first public API + modern security boundaries**:

1. **Naming/framework** — PascalCase public surface; camelCase parameters; standard prefixes/suffixes; scenario namespaces.
2. **API design** — aggregate entry types; create-set-call; collections not raw arrays; properties vs methods rules.
3. **Exceptions/events** — specific exceptions; EventHandler&lt;T&gt;; no public fields; IDisposable for native resources.
4. **Security/verify** — no legacy sandbox APIs; treat untrusted input carefully; Roslyn analyzers/CLS on libraries.

## Decision tables

### Naming (FDG digest + MS docs)

| Entity | Convention |
|---|---|
| Public types/members | PascalCase |
| Parameters | camelCase |
| Type parameters | `T` or `T` + role (`TSession`) |
| Interfaces | `I` prefix |
| Acronyms | ≤2 chars all caps in type names; longer: `HtmlButton` |
| Avoid | Hungarian, underscores, contractions (`GetWin`) |
| Types/properties | nouns / noun phrases |
| Methods/events | verbs; events present/past (`Closing`/`Closed`) |
| Suffixes | `Exception`, `EventArgs`, `EventHandler`, `Attribute`, `Collection`, `Dictionary` |
| Namespaces | `Company.Product.Feature` — scenario-based, not org chart |
| CLR names | `ToInt64` not `ToLong` in language-neutral API |

### API design

| Case | Rule |
|---|---|
| Scenarios | write desired consumer code first; design API from samples |
| Entry types | one aggregate component name per feature area |
| Simplicity | main scenarios ≤ few lines; avoid multi-object ceremony |
| Style | create → set properties → call method/event |
| Returns/inputs | most derived return; least derived parameters |
| Collections | prefer `Collection<T>`/`ReadOnlyCollection<T>` over arrays/`List<T>` in public API |
| Fields | never public; use properties |
| Virtual/sealed | avoid unless strong reason |
| Interfaces | ship with concrete impl + at least one consumer API |
| CLS | `[CLSCompliant(true)]` on libraries |

### Exceptions & resources

| Case | Rule |
|---|---|
| Failures | exceptions, not error codes |
| Throw | specific types (`ArgumentNullException`, …); not bare `Exception` |
| Catch | avoid catching `Exception` base |
| Events | `EventHandler<TEventArgs>`; prefer events over delegate properties |
| Dispose | `IDisposable` for native resources; avoid finalizers |
| Overloads | consistent parameter order; core on widest overload |
| out/ref | avoid in public API |

### Security baseline

| Case | Rule |
|---|---|
| Do not use | CAS, partial trust, APTCA, Remoting, DCOM, binary formatters |
| Boundaries | OS isolation, containers, process identity — not CAS stack walks |
| Untrusted input | validate/sanitize Internet and external input |
| Native wrappers | limit unmanaged rights to wrapper; assert/demand appropriately |
| Resource libraries | demand permission before exposing files/network/unmanaged |
| Apps vs libraries | apps simpler; libraries assume malicious callers |

## Anti-patterns

- Org-chart namespace hierarchy
- Best name on abstract base instead of aggregate entry type
- Multi-step object graph for simple scenario
- `ArrayList`/`Hashtable`/`Dictionary<K,V>` in public API surface
- Public fields
- Throwing `Exception`/`SystemException`
- Empty catch of `Exception`
- Custom exception when BCL type fits
- `BeforeClick`/`AfterClick` event names
- `StatusEnum` type name or enum value prefixes
- Sealed types without justification
- Interface shipped without concrete type and consumer
- Mutable public value types
- Public nested types without need
- BinaryFormatter/NetRemoting in new code
- APTCA on libraries
- Assuming partial-trust callers
- Skipping analyzer/CLS check on reusable library
- Duplicating FDG naming in language-specific skill instead of referencing this row

## Skill trace

| Artifact | Role |
|---|---|
| `dotnet-style-naming-framework.md` | Pascal/camel, suffixes, namespaces |
| `dotnet-style-api-design.md` | scenarios, aggregates, collections |
| `dotnet-style-exceptions-events.md` | throw/catch, events, dispose |
| `dotnet-style-security-verify.md` | secure baseline, analyzers, CLS |
| `dotnet-coding-practices/SKILL.md` | router + library CI gates |

## Language routing

| Language | Syntax/layout skill |
|---|---|
| C# | `csharp-coding-practices` |
| Visual Basic .NET | `vb-coding-practices` |
| F# | `fsharp-coding-practices` |
