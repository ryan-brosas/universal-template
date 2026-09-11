<!-- capsule-v2 -->
# Formatting and names — does code pass dart format and naming rules?

**Source:** Effective Dart — Style. **Question:** Are identifiers and imports formatted consistently?

## Format seam
**Path/Symbol:** Dart libraries under `lib/` and `test/`.
**Signature:** `dart format`; ≤80 columns; braces on all control flow.
**Data Shape:** sorted import sections.

### Decisive pattern
```dart
import 'dart:async';

import 'package:meta/meta.dart';

import '../src/models/user.dart';

class UserRepository {
  Future<User?> findById(String userId) {
    if (userId.isEmpty) {
      return Future.value(null);
    }
    return _load(userId);
  }
}
```

**Flow:** run `dart format` on every change → prefer ≤80 columns → always use `{}` on `if`/`for`/`while` → order imports: `dart:` then `package:` then relative, each section alphabetical → exports after imports.
**Invariant:** unformatted diff, import order violations, or braceless single-line control flow fail review.
**Probe:** `dart format --output=none --set-exit-if-changed`; analyzer import lints.

## Naming seam
```dart
// file: user_repository.dart
class HttpClientAdapter {}

const defaultTimeout = Duration(seconds: 30);

String buildAuthHeader(String rawToken) => 'Bearer $rawToken';
```

**Flow:** UpperCamelCase types/extensions → lowerCamelCase members → lowerCamelCase constants (preferred) → lowercase_with_underscores files/packages → acronym capitalization like words (`HttpRequest` not `HTTPRequest`) → `_` prefix only for private.
**Invariant:** `user_repository.dart` with class `userRepo`, or public `leading_underscore`, fails review.
**Probe:** naming lint rules; file name matches primary public type pattern review.

## Verdict
dart format, import order, camelCase/snake_case by construct. Learning note: `dart-style-learning-note.md`.
