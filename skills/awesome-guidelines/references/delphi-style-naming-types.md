<!-- capsule-v2 -->
# Naming and types — do identifiers follow Pascal and prefix rules?

**Source:** Embarcadero General Rules + Type Declarations; DelphiStandards §2. **Question:** Can readers tell types, fields, and parameters apart by name?

## Type seam
**Path/Symbol:** type declarations in interface sections.
**Signature:** PascalCase; `T`/`I`/`E`/`P` prefixes.
**Data Shape:** no underscores in Delphi names (except API translations).

### Decisive pattern
```pascal
type
  TCustomer = class
  private
    FName: string;
    FActive: Boolean;
  public
    function IsValidEmail(const AEmail: string): Boolean;
  end;

  ICustomerRepository = interface
    function FindById(const AId: Integer): TCustomer;
  end;

  ECustomerNotFound = class(Exception);

  PCustomer = ^TCustomer;
```

**Flow:** PascalCase descriptive names → `T` classes/records → `I` interfaces → `E` exceptions → `P` pointers → class fields `F` prefix → parameters `A` prefix + `const` when immutable → locals `L` prefix (team) → methods verbs / boolean `Is`/`Has`.
**Invariant:** `snake_case`, `Tcustomer`, public `Name` field without property, or `Int` abbreviations fail review.
**Probe:** naming checklist; grep `_` in identifiers outside WinAPI imports.

## Component and constant seam
```pascal
const
  cDefaultTimeoutMs = 5000;
  scLoginFailedMessage = 'Invalid credentials.';

var
  ButtonLogin: TButton;
  EditUserName: TEdit;
```

**Flow:** UI components use type-leading names (`ButtonLogin`) without F/L → string constants `sc*` / numeric `c*` → retain foreign API symbol casing in translations (`WM_LBUTTONDOWN`).
**Invariant:** `btnLogin` camelCase component or ALL_CAPS app constant fails review.
**Probe:** form/datamodule field audit.

## Verdict
PascalCase, T/I/E/F/A/L conventions, API translation exceptions only. Learning note: `delphi-style-learning-note.md`.
