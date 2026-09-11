<!-- capsule-v2 -->
# Formatting and headers — are includes self-contained and layout consistent?

**Source:** Google C++ style guide §Header Files, §Formatting. **Question:** Will headers compile alone and match project layout probes?

## Header seam
**Path/Symbol:** `.h` / `.cc` pairs in C++ modules.
**Signature:** self-contained header + `#define` guard + direct includes only.
**Data Shape:** `.cc` for implementation; `.inc` only for exceptional mid-file includes.

### Decisive pattern
```cpp
#ifndef MYPROJECT_HTTP_SERVER_LOGS_H_
#define MYPROJECT_HTTP_SERVER_LOGS_H_

#include <string>
#include <vector>

#include "myproject/logging/log_entry.h"

class LogWriter {
 public:
  void Write(const std::vector<LogEntry>& entries);
};

#endif  // MYPROJECT_HTTP_SERVER_LOGS_H_
```

**Flow:** one primary `.h` per `.cc` → guard name from project/path/file → include every symbol's declaring header directly → no `-inl.h` splits for templates used by clients.
**Invariant:** relying on transitive includes or missing guards fails review.
**Probe:** include-what-you-use (IWYU) / clang-include-fixer clean on changed files.

## Layout seam
```cpp
ReturnType ClassName::FunctionName(Type param_one, Type param_two) {
  DoSomething();
  if (condition) {
    return value;
  }
  return other;
}
```

**Flow:** 2-space indent → return type same line as function name when fits → opening brace on same line as signature → 4-space indent for wrapped parameters.
**Invariant:** K&R variant mixing (Allman braces for functions) or tabs fail review in Google-style trees.
**Probe:** `clang-format --dry-run` / project formatter check passes.

## Verdict
Self-contained headers, IWYU, guarded includes, 2-space clang-format layout. Learning note: `cpp-style-learning-note.md`.
