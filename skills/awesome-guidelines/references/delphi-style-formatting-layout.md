<!-- capsule-v2 -->
# Formatting and layout — is whitespace and block structure consistent?

**Source:** Embarcadero White Space + General Rules; DelphiStandards §1. **Question:** Does layout match 2-space Pascal conventions?

## Layout seam
**Path/Symbol:** `.pas` units in Delphi projects.
**Signature:** 2-space indent; lowercase keywords; unit keywords flush left.
**Data Shape:** `begin`/`end` on separate lines.

### Decisive pattern
```pascal
unit Customer.Manager;

interface

uses
  System.SysUtils,
  System.Classes;

type
  TCustomerManager = class
  public
    procedure LoadCustomers;
  end;

implementation

procedure TCustomerManager.LoadCustomers;
begin
  if FCustomers.Count = 0 then
  begin
    ReloadFromDatabase;
  end;
end;

end.
```

**Flow:** two spaces per level → `unit`/`uses`/`interface`/`implementation`/`end.` at margin → lowercase keywords/directives → `begin`/`end` on own lines → spaces around binary operators → continuation lines indented +2 from first line, never starting with operator.
**Invariant:** tab indentation, indented unit keywords, or uppercase `BEGIN` fail review.
**Probe:** IDE formatter / project `.editorconfig` (indent 2); manual review on wrapped lines.

## Line length seam
**Flow:** prefer ≤120 columns → break long calls with aligned args → don't split parameter from type mid-list except comma-grouped same-type params.
**Invariant:** unbroken 200+ character lines fail review without team waiver.
**Probe:** IDE vertical guideline at 120; formatter wrap check.

## Verdict
2-space flush-unit layout, lowercase keywords, begin/end blocks. Learning note: `delphi-style-learning-note.md`.
