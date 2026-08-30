<!-- capsule-v2 -->
# Resources, errors, and docs — are lifetimes and API documented?

**Source:** DelphiStandards §4–5, §9; Embarcadero general practice. **Question:** Are objects freed, exceptions handled, and public API documented?

## Resource seam
**Path/Symbol:** object creation/destruction in methods.
**Signature:** `try..finally` with `FreeAndNil`.
**Data Shape:** nil-init locals before try.

### Decisive pattern
```pascal
function LoadCustomer(const AId: Integer): TCustomer;
var
  LQuery: TFDQuery;
begin
  Result := nil;
  LQuery := nil;
  try
    LQuery := TFDQuery.Create(nil);
    LQuery.SQL.Text := 'select * from customers where id = :id';
    LQuery.ParamByName('id').AsInteger := AId;
    LQuery.Open;
    Result := MapRow(LQuery);
  finally
    FreeAndNil(LQuery);
  end;
end;
```

**Flow:** assign nil before try → create inside try → `FreeAndNil` in `finally` → use typed `except on E:` only when handling → re-raise with `raise` when propagating → never empty except (except documented critical logging/finalization).
**Invariant:** bare `.Free` without nil, missing finally on Create, or `except end;` swallow fails review.
**Probe:** code review on every `Create`; static analyzer rules where available.

## Properties and docs seam
```pascal
/// <summary>
/// Returns whether the customer record is active.
/// </summary>
function IsActive: Boolean;

property Active: Boolean read FActive write SetActive;
```

**Flow:** properties instead of public fields → XML `///` on exported methods/classes → summary + param tags → getters must not surprise side effects.
**Invariant:** public `FActive: Boolean` field or exported method without summary fails review.
**Probe:** documentation coverage report; XML doc compile warnings.

## Verdict
FreeAndNil finally blocks, typed except, properties, XML docs. Learning note: `delphi-style-learning-note.md`.
