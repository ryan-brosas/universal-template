<!-- capsule-v2 -->
# Naming and types — are keywords lowercase and types pointer-clear?

**Source:** FPC wiki §Keywords/Classes; GNU GPC §5.6/5.5. **Question:** Can readers distinguish keywords, types, and enum groups at a glance?

## Naming seam
**Path/Symbol:** types, constants, identifiers in interface/implementation.
**Signature:** lowercase keywords; PascalCase identifiers; `P`/`T` pointer pairs.
**Data Shape:** `PMyRec = ^TMyRec` before `TMyRec`.

### Decisive pattern
```pascal
type
  pmyint = ^tmyint;
  tmyint = integer;

  tfoobarb = (fb_foo, fb_bar, fb_baz);

const
  mf_foo = 1;
  mf_bar = 3;

function getter: boolean;
  begin
    result:=true;
  end;
```

**Flow:** write keywords and directives lowercase (`begin`, `procedure`, `protected`) → identifiers PascalCase concatenated words (`BlockRead`, `WriteLn`, `IOResult`); short locals lowercase (`i`, `s1`) → declare pointer type before record/type (`PStrList = ^TStrList`; put `Next` first in recursive lists) → enum/const groups may use two-letter lowercase prefix + underscore (`fb_Foo`, `mf_Bar`) → acronyms consistent (`GPC`, `EOF`, `WriteLn`) → avoid underscores in general identifiers → if macros/conditionals unavoidable, ALL_CAPS_WITH_UNDERSCORES.
**Invariant:** uppercase keywords, snake_case general identifiers, or pointer after forward type without `P` prefix fails review.
**Probe:** LowercaseKeywords rule; T/P pair audit on new types.

## Class seam
**Flow:** class sections at same indent as class name (FPC); object areas ordered fields → constructors → destructor → methods.
**Invariant:** visibility blocks out of order fail API readability review.
**Probe:** section order spot check on new objects.

## Verdict
Lowercase keywords, PascalCase API, explicit P/T pairs. Learning note: `pascal-style-learning-note.md`.
