<!-- capsule-v2 -->
# Formatting and layout — is indentation stable across editors and dialects?

**Source:** FPC wiki §Indentation/Spaces; GNU GPC §5.3/5.8/5.9. **Question:** Does the file declare FPC-tight or GPC-spaced conventions and stick to them?

## Layout seam
**Path/Symbol:** `.pas`/`.pp` units (FPC compiler, GPC, non-Lazarus Pascal).
**Signature:** 2-space indent; no tabs; `begin`/`end` on own lines.
**Data Shape:** FPC `p:=x+1` or GPC `Inc (x)` spacing profile.

### Decisive pattern
```pascal
{ fpc compiler style }
procedure do_this;
  var
    i: integer;
  begin
    i:=0;
    if i=0 then
      begin
        result:=true;
      end;
  end;


{ gnu gpc style }
procedure DoThis;
var
  I: Integer;
begin
  I := 0;
  if I = 0 then
    begin
      DoThis := True;
    end;
end;
```

**Flow:** indent 2 spaces per level; never tabs → put `begin`/`end` on their own lines; do not attach `then begin` on one line → FPC compiler/RTL: no spaces around operators/colons (`p:=p+i`) → GNU GPC published code: space before `(` in calls and after keywords where manual shows `Inc (x)` → split composite conditions across lines when operands are non-trivial → `else` in `else if` chains aligns with first `if`, not extra-indented → separate subroutines with blank lines (FPC: two blanks between; GPC: empty line between blocks) → keep lines ~68–78 cols when wrapping (GPC guidance).
**Invariant:** tabs, uppercase keywords, or mixed FPC/GPC spacing in one tree fails review.
**Probe:** fpsonar NoTabs/LowercaseKeywords/BeginEndRequired; visual spacing profile grep.

## Nesting seam
**Flow:** indent routine `var`/`const`/`begin` sections one level under header (FPC compiler); FCL/GPC top-level routines not indented → nested functions same level as local `var`.
**Invariant:** FCL file using compiler-style indented procedure headers fails package convention review.
**Probe:** routine header indent check against project baseline (FPC vs FCL).

## Verdict
Two-space, own-line begin/end, project-consistent operator spacing. Learning note: `pascal-style-learning-note.md`.
