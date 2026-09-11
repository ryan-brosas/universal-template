# Delphi / Object Pascal style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `delphi-style-*.md` capsules, `delphi-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Embarcadero General Rules](https://docwiki.embarcadero.com/RADStudio/Athens/en/General_Rules) (primary) | descriptive PascalCase identifiers; lowercase keywords/directives; 2-space indent (no tabs); US-ASCII; no underscores except API/header translations |
| [Embarcadero White Space Usage](https://docwiki.embarcadero.com/RADStudio/Sydney/en/White_Space_Usage) (primary) | spaces around operators; unit-level keywords flush margin; continuation lines +2 indent; don't break before binary operator on wrap |
| [Embarcadero Type Declarations](https://docwiki.embarcadero.com/RADStudio/Athens/en/Type_Declarations) (primary) | `T` types, `E` exceptions, `I` interfaces, `P` pointers; `F` private fields; `type` section indent |
| [DelphiStandards v2.1 (omonien)](https://github.com/omonien/DelphiStandards) (secondary) | `L`/`A`/`F`/`G` prefixes; `.Form`/`.DM` unit hierarchy; 120 cols; `FreeAndNil`; XML `///` docs; generics collections |

**Fetch note:** Alexandria style guide index returned Cloudflare on direct fetch; Athens/Sydney topic pages indexed above supply official rules. Community guide reconciled where it extends (not contradicts) Embarcadero baseline.

## Mental model

Delphi style pairs **Embarcadero PascalCase discipline** with **modern unit hierarchy**:

1. **Layout** — 2 spaces; `begin`/`end` on own lines; unit keywords flush left; ≤120 columns (modern teams).
2. **Naming** — PascalCase everywhere; `T`/`I`/`E` types; `F` fields; `A` params; `L` locals (team convention); lowercase keywords.
3. **Units** — hierarchical `Customer.Details.Form` ↔ `TFormCustomerDetails` ↔ `FormCustomerDetails`; interface vs implementation uses.
4. **Resources** — `try..finally` + `FreeAndNil`; typed `except on E:` when handling; properties over public fields.
5. **Docs** — XML doc comments on public API; verb methods; boolean `Is`/`Has` prefixes.

## Decision tables

### Formatting

| Topic | Rule |
|---|---|
| Indent | 2 spaces; never tabs |
| Keywords | lowercase (`begin`, `type`, `class`) |
| Unit scope | `unit`, `uses`, `interface`, `implementation`, `end.` flush left |
| Lines | soft ≤120; wrap with +2 indent; no leading binary op on continuation |
| Blocks | `begin`/`end` separate lines; braces on control flow |

### Naming

| Entity | Convention |
|---|---|
| Types/classes/records | `T` + PascalCase (`TCustomer`) |
| Interfaces | `I` + PascalCase |
| Exceptions | `E` + PascalCase |
| Fields (class) | `F` + PascalCase |
| Parameters | `A` + PascalCase; prefer `const` |
| Locals | `L` + PascalCase (modern team) |
| Components | type prefix, no F/L (`ButtonLogin`) |
| Constants | `c`/`sc` prefix or ALL_CAPS for build flags |
| API imports | retain foreign casing (`WM_LBUTTONDOWN`) |

### Units & classes

| Topic | Rule |
|---|---|
| Form units | `Area.Form.pas` → `TFormArea` |
| Data modules | `Area.DM.pas` → `TDMArea` |
| Uses | system → third-party → own; impl-only in implementation |
| Fields | private `F*`; expose via properties |
| Records | public fields OK; no `F` on record fields |

### Errors & resources

| Case | Rule |
|---|---|
| Ownership | `try..finally` + `FreeAndNil` |
| Handling | `except on E: TException` — never empty except |
| Re-raise | `raise` after log when propagating |
| Critical cleanup | documented silent except only in logging/finalization |

## Anti-patterns

- snake_case identifiers (except platform headers)
- Tabs for indentation
- Public fields on classes (use properties)
- `.Free` without nil assignment on locals
- Empty `except` blocks
- `with` for non-trivial scope (hard to read)
- Monolithic unit names without hierarchy
- Underscores in Delphi identifiers (non-API)
- ALL_CAPS consts for ordinary app constants
- Missing XML docs on exported API

## Skill trace

| Artifact | Role |
|---|---|
| `delphi-style-formatting-layout.md` | indent, begin/end, whitespace |
| `delphi-style-naming-types.md` | T/I/E/F/A/L, PascalCase |
| `delphi-style-units-structure.md` | namespace units, uses, classes |
| `delphi-style-resources-errors.md` | try/finally, except, properties, docs |
| `delphi-coding-practices/SKILL.md` | Delphi IDE formatter + Pascal analyzer in CI |
