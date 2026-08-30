<!-- capsule-v2 -->
# Formatting and layout — are selectors and imports mechanically consistent?

**Source:** Google §Spacing and Formatting; GitHub §Whitespace/Control Structures. **Question:** Can reviewers scan `@interface` blocks and message sends without mixed brace/import styles?

## Layout seam
**Path/Symbol:** `.h`/`.m`/`.mm` translation units.
**Signature:** 2-space indent; braces on control-line; colon-aligned multiline selectors.
**Data Shape:** grouped `#import` blocks with blank separators.

### Decisive pattern
```objc
#import "ProjectX/FooViewController.h"

#import <Foundation/Foundation.h>

#include <vector>

#import "ProjectX/FooModel.h"

@implementation FooViewController

- (void)configureWithName:(NSString *)name
                   error:(NSError **)error {
  if (!name) {
    if (error) {
      *error = [NSError errorWithDomain:FooErrorDomain
                                   code:FooErrorMissingName
                               userInfo:nil];
    }
    return;
  }
  _name = [name copy];
}

@end
```

**Flow:** indent with 2 spaces; trim trailing whitespace; end files with newline → put opening `{` on same line as `if`/`for`/`@implementation`; when `else` exists, brace both branches → format message sends all-on-one-line OR one parameter per line with colons aligned (pick file-consistent style) → indent continuation lines ≥4 spaces beyond first keyword when colons align → include order: related header, system frameworks (umbrella), C/C++ libs, project headers; blank line between groups → prefer `@import UIKit` or `#import <Foundation/Foundation.h>` over many subframework headers.
**Invariant:** tabs in Google-aligned trees, `else` single-line without braces, or mixed colon-alignment styles in one file fail review.
**Probe:** clang-format dry-run; import-order lint; visual selector alignment check.

## Control-flow seam
**Flow:** early `return`/`break` allowed; single-line `if` without `else` may stay on one line; space after keywords before `(`; no space inside parentheses.
**Invariant:** multi-statement `if/else` without braces fails review.
**Probe:** brace-style spot check on changed control flow.

## Verdict
Two-space, braced control flow, aligned selectors, grouped umbrella imports. Learning note: `objc-style-learning-note.md`.
