<!-- capsule-v2 -->
# Comments and control — are docs brace-shaped and control flow Pascal-safe?

**Source:** GNU GPC §5.4/5.7/5.1; FPC wiki §Comments/Routines. **Question:** Would a maintainer disable code safely and avoid undefined loop behavior?

## Comment seam
**Path/Symbol:** interface docs, inline comments, compiler directives.
**Signature:** `{ spaced braces }`; English; `{$if False}` for disabled code.
**Data Shape:** interface comment per exported declaration (GPC).

### Decisive pattern
```pascal
{ Returns true when buffer contains valid header.
  AValue may be nil only when AllowEmpty is set. }
function parseheader(var avalue: tbuffer): boolean;

procedure demo;
  var
    x: integer;
  begin
    x:=1;
    inc(x);  { Increment after init. }
  end;

{$if False}
  { Temporary experiment — remove before release. }
  callbrokenapi;
{$endif}
```

**Flow:** use `{ single space inside braces }` only in published code — no `(* *)` or `//` (GPC); write comments in English at same indent as described code → document every interface declaration (GPC); end-of-line comments need two spaces before `{` → use `{$if False}…{$endif}` to exclude code, not comment blocks → directives as `{$name}` on own lines; no comments inside directives → mark temporary issues with `@@` fixme comments separately from normal docs → FPC functions assign `result`, not function name; GPC prefers `function Foo = Bar: Integer` over implicit Result → avoid goto/Exit/Break/Continue when a clear loop/if suffices → never modify `for` counter or rely on value after loop → put more-variable expression on left in comparisons.
**Invariant:** `//` comments in GPC-published code, commented-out API left in compile path, or `for` counter mutation fails review.
**Probe:** comment-style grep; control-flow audit; `-Wall` compile.

## Verify seam
**Flow:** run `fpc -Wall` (and `-O3` per GPC) on changed units; optional fpsonar (NoTabs, LowercaseKeywords, BeginEndRequired, LineTooLong).
**Invariant:** style regressions without NOLINT/fixme rationale fail CI.
**Probe:** CI build log; fpsonar report if configured.

## Verdict
Brace comments, directive-guarded disables, result-safe functions, -Wall-clean builds. Learning note: `pascal-style-learning-note.md`.
