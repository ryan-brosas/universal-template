<!-- capsule-v2 -->
# Units and structure — is each file one module with ordered declarations?

**Source:** GNU GPC §5.5/5.1; FPC wiki §Routines/FCL. **Question:** Does interface order match implementation and avoid cyclic uses?

## Unit seam
**Path/Symbol:** program/unit `.pas` files and `uses` clauses.
**Signature:** lowercase filename; header comment; const→type→var→label→routines.
**Data Shape:** implementation routines mirror interface order.

### Decisive pattern
```pascal
{ Short description of unit purpose.
  Longer detail and sources.
  Copyright (C) 2026 Author
  License: GPL/LGPL as project requires. }

unit myutils;

interface

uses
  sysutils;

const
  defaultcount = 10;

type
  pitem = ^titem;
  titem = record
    next: pitem;
    value: integer;
  end;

function createitem(avalue: integer): pitem;

implementation

function createitem(avalue: integer): pitem;
  begin
    result:=nil;
  end;

end.
```

**Flow:** one program/unit/module per file; lowercase `.pas` filename matching unit name → start file with description/copyright/license comment (GPC) → order declaration blocks const → type → var → label → routines unless dependency forces deviation → keep related constants with their part of large units, not one giant const section → implementation bodies follow interface declaration order → avoid unit cycles; prefer `uses` in implementation → FCL/GPC: do not indent global routine bodies; FPC compiler tree indents nested sections → omit empty unit initializer `begin end.` → case branches: semicolon before `else` branch per GPC dangling-else guard.
**Invariant:** multiple units per file, cyclic interface uses, or implementation order drift from interface fails review.
**Probe:** uses-cycle grep; interface/implementation order diff on changed units.

## File seam
**Flow:** compile with `-Wall` clean (GPC); enable range/overflow checks in Lazarus-bound code when project requires (see DesignGuidelines).
**Invariant:** new warnings in CI fail gate.
**Probe:** `fpc -Wall` or project build flags on changed units.

## Verdict
Single-unit files, ordered blocks, mirrored implementation, acyclic uses. Learning note: `pascal-style-learning-note.md`.
