<!-- capsule-v2 -->
# Library structure — do .h/.cpp, guards, and class layout match the Morse template?

**Source:** Writing a Library for Arduino. **Question:** Are header/source split, include guards, and private `_field` convention correct with hardware init deferred to `begin()`?

## File seam
**Path/Symbol:** `LibraryName/` under sketchbook or repo `libraries/`.
**Signature:** `LibraryName.h` + `LibraryName.cpp`; optional `keywords.txt`, `examples/`, `library.properties`.
**Data Shape:** one primary class per library folder; `.h` declarations, `.cpp` definitions.

### Decisive pattern
```arduino
#ifndef Morse_h
#define Morse_h

#include "Arduino.h"

class Morse {
  public:
    Morse(int pin);
    void begin();
    void dot();
    void dash();
  private:
    int _pin;
};

#endif
```

**Flow:** create paired `.h` and `.cpp` with exact extensions (not `.cpp.txt`) → header: license comment, guard macro `Name_h`, `#include "Arduino.h"`, class declaration → source: `#include "Arduino.h"` and `#include "Name.h"`, then `Class::method` bodies → place public methods first in class; private members with leading underscore matching header → add file header comment (name, description, author, date, license) on both files.
**Invariant:** library without `"Arduino.h"` in header, missing include guard, or mismatched `_member` name between .h/.cpp fails structure review.
**Probe:** list library dir; verify `.h`/`.cpp` pair; `#ifndef`/`#define`/`#endif` present; `_pin`-style private fields consistent.

## Constructor vs begin seam
**Flow:** constructor assigns parameters to private fields only → `begin()` calls `pinMode`, bus init, sensor configuration → sketch calls `instance.begin()` inside `setup()` after global constructors run.
**Invariant:** `pinMode`/`Wire.begin`/sensor start inside constructor is a defect.
**Probe:** constructor diff empty of hardware calls; `begin()` contains `pinMode` or bus setup.

## Implementation seam
```arduino
void Morse::begin() {
  pinMode(_pin, OUTPUT);
}

void Morse::dot() {
  digitalWrite(_pin, HIGH);
  // ...
}
```

**Flow:** prefix definitions with `ClassName::` → use `_field` names from header, not bare parameter names → keep implementation in `.cpp`, not duplicated in header unless inline template requirement.
**Invariant:** method body using wrong member name or missing scope prefix fails link/compile.
**Probe:** compile example sketch; verify symbols resolve.

## Verdict
Guarded header, Arduino.h, ctor config-only, begin() for HW, underscore private fields, Class:: definitions in .cpp. Learning note: `arduino-style-learning-note.md`.
