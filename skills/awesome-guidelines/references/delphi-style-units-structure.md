<!-- capsule-v2 -->
# Units and structure — are modules organized with clear hierarchy?

**Source:** DelphiStandards §3; Embarcadero unit rules. **Question:** Do unit names, classes, and uses clauses reflect project structure?

## Unit hierarchy seam
**Path/Symbol:** project `.pas` files and matching unit names.
**Signature:** dotted namespace units; `.Form`/`.DM` suffixes.
**Data Shape:** interface public / implementation private split.

### Decisive pattern
```pascal
unit Customer.Details.Form;

interface

uses
  System.Classes, Vcl.Controls, Vcl.Forms,
  Customer.Details.DM;

type
  TFormCustomerDetails = class(TForm)
    DMCustomerDetails: TDMCustomerDetails;
    ButtonSave: TButton;
  end;

var
  FormCustomerDetails: TFormCustomerDetails;

implementation

uses
  System.SysUtils;

{$R *.dfm}

end.
```

**Flow:** file `Customer.Details.Form.pas` ↔ `unit Customer.Details.Form` ↔ class `TFormCustomerDetails` ↔ instance `FormCustomerDetails` → data modules use `.DM` suffix → group `uses`: system → libraries → own units → implementation-only uses in `implementation`.
**Invariant:** flat `Unit1.pas` in multi-form app or mismatched unit/file/class triple fails review.
**Probe:** project tree review; grep `uses` for circular or `implementation`-only deps in interface.

## Class structure seam
**Flow:** public API in interface → private fields `F*` → expose via properties → sealed utility classes for static helpers → prefer generics (`TList<T>`, `TArray<T>`) over untyped lists.
**Invariant:** business logic units importing VCL in interface when only impl needs it fails review.
**Probe:** uses-clause analyzer; dependency direction review.

## Verdict
Dotted unit hierarchy, Form/DM suffixes, clean interface/implementation uses. Learning note: `delphi-style-learning-note.md`.
